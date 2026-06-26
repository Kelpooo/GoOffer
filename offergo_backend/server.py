"""HTTP server for the OfferGo MVP application."""

import io
import json
import os
import re
import sys
import traceback
import urllib.error
import urllib.request
import uuid
import zipfile
from http import HTTPStatus
from http.cookies import SimpleCookie
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs
from xml.etree import ElementTree as ET

from offergo_backend.auth import (
    AUTH_COOKIE_NAME,
    SESSION_MAX_AGE_SECONDS,
    build_password_policy,
    hash_password,
    new_session_id,
    new_user_id,
    normalize_username,
    now_iso,
    session_expires_at,
    validate_password,
    validate_username,
    verify_password,
)
from offergo_backend.config import load_settings
from offergo_backend.database import (
    create_auth_session,
    create_user,
    delete_auth_session,
    get_account_overview,
    get_user_progress_payload,
    get_auth_session_user,
    get_user_auth_record_by_id,
    get_user_by_username,
    initialize_database,
    ensure_questions_seeded,
    load_questions_payload,
    merge_progress_into_user,
    sync_user_progress,
    update_user_password,
    upsert_question_progress,
)
from offergo_backend.storage import FileVisitorTracker, InMemoryResumeSessionStore, SqliteVisitorTracker


SETTINGS = load_settings()
BASE_DIR = SETTINGS.base_dir
WEB_DIR = SETTINGS.web_dir
PROMPT_FILE = SETTINGS.prompt_file

COMMON_TECH_KEYWORDS = [
    "React",
    "Vue",
    "TypeScript",
    "JavaScript",
    "Node.js",
    "HTML",
    "CSS",
    "Webpack",
    "Vite",
    "Next.js",
    "MySQL",
    "Redis",
    "Java",
    "Spring",
    "Spring Boot",
    "Go",
    "Python",
    "Docker",
    "Kubernetes",
    "Linux",
    "MQ",
    "Kafka",
    "RabbitMQ",
    "RAG",
    "Agent",
    "Prompt",
    "LangChain",
    "向量数据库",
    "大模型",
    "性能优化",
    "工程化",
    "微服务",
    "分布式",
    "高并发",
]


def load_prompt_templates():
    with PROMPT_FILE.open("r", encoding="utf-8") as file:
        return json.load(file)


PROMPTS = load_prompt_templates()
PASSWORD_POLICY = build_password_policy()

RESUME_LLM_API_KEY_ENV_VARS = (
    "RESUME_REVIEW_API_KEY",
    "DEEPSEEK_API_KEY",
    "OPENAI_API_KEY",
)
RESUME_LLM_API_URL_ENV_VARS = (
    "RESUME_REVIEW_API_URL",
    "DEEPSEEK_API_URL",
    "OPENAI_API_URL",
)
RESUME_LLM_MODEL_ENV_VARS = (
    "RESUME_REVIEW_MODEL",
    "DEEPSEEK_MODEL",
    "OPENAI_MODEL",
)
RESUME_LLM_MAX_TOKENS_ENV_VAR = "RESUME_REVIEW_MAX_TOKENS"

STRUCTURED_OUTPUT_HINT = (
    "\n\n请只输出 JSON 对象，不要输出代码块或额外说明。"
    "\n返回示例（仅作结构参考，不要照抄内容）："
    '{"overallScore":80,"summary":"...","dimensionScores":[{"name":"技术栈","score":80,"verdict":"较为完整","reasoning":"..."}],'
    '"jobMatch":{"targetRole":"...","matchScore":80,"reasoning":"...","matchedKeywords":["..."],"missingKeywords":["..."]},'
    '"highlights":["..."],"risks":["..."],"suggestions":["..."],"rewrittenBullets":["..."]}'
)


class UploadedFile:
    def __init__(self, filename, content):
        self.filename = filename
        self.file = io.BytesIO(content)


class SimpleForm(dict):
    def getfirst(self, key, default=""):
        value = self.get(key, default)
        if isinstance(value, list):
            return value[0] if value else default
        return value


def first_non_empty_env(*names, default=""):
    for name in names:
        value = os.environ.get(name, "").strip()
        if value:
            return value
    return default


def resolve_resume_llm_config():
    model = first_non_empty_env(*RESUME_LLM_MODEL_ENV_VARS, default=SETTINGS.deepseek_model)
    if model.startswith("DEEPSEEK_MODEL=") or model.startswith("OPENAI_MODEL=") or model.startswith("RESUME_REVIEW_MODEL="):
        model = model.split("=", 1)[1].strip()
    return {
        "api_key": first_non_empty_env(*RESUME_LLM_API_KEY_ENV_VARS),
        "api_url": first_non_empty_env(*RESUME_LLM_API_URL_ENV_VARS, default=SETTINGS.deepseek_api_url),
        "model": model,
        "max_tokens": int(os.environ.get(RESUME_LLM_MAX_TOKENS_ENV_VAR, "2500")),
    }


def json_response(handler, status, payload):
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    handler.send_response(status)
    handler.send_header("Content-Type", "application/json; charset=utf-8")
    handler.send_header("Content-Length", str(len(body)))
    handler.end_headers()
    handler.wfile.write(body)


def current_timestamp():
    from datetime import datetime, timezone

    return datetime.now(timezone.utc).isoformat()


RESUME_SESSIONS = InMemoryResumeSessionStore()


def build_visitor_tracker():
    if SETTINGS.storage_mode == "sqlite":
        return SqliteVisitorTracker(SETTINGS.app_db_path, current_timestamp)
    return FileVisitorTracker(SETTINGS.visitor_stats_path, current_timestamp)


VISITOR_TRACKER = build_visitor_tracker()


def load_questions_response():
    if SETTINGS.storage_mode == "sqlite":
        return load_questions_payload(SETTINGS.app_db_path)
    with (WEB_DIR / "data" / "questions.json").open("r", encoding="utf-8") as file:
        return json.load(file)


class ResumeReviewHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(BASE_DIR), **kwargs)

    def do_GET(self):
        if self.path in {"/", ""}:
            self.send_response(HTTPStatus.FOUND)
            self.send_header("Location", "/web_mvp/")
            self.end_headers()
            return
        if self.path == "/web_mvp":
            self.send_response(HTTPStatus.FOUND)
            self.send_header("Location", "/web_mvp/")
            self.end_headers()
            return
        if self.path == "/api/health":
            return json_response(self, HTTPStatus.OK, {"ok": True, "service": "resume-review"})
        if self.path == "/api/site-stats":
            return json_response(self, HTTPStatus.OK, VISITOR_TRACKER.get_public_stats())
        if self.path == "/api/questions":
            return json_response(self, HTTPStatus.OK, load_questions_response())
        if self.path == "/api/auth/me":
            return self.handle_auth_me()
        if self.path == "/api/account/overview":
            return self.handle_account_overview()
        if self.path == "/api/user-progress":
            return self.handle_get_user_progress()
        if self.path in {"/web_mvp/", "/web_mvp/index.html"}:
            return self.serve_tracked_index()
        return super().do_GET()

    def do_POST(self):
        try:
            if self.path == "/api/auth/register":
                return self.handle_auth_register()
            if self.path == "/api/auth/login":
                return self.handle_auth_login()
            if self.path == "/api/auth/logout":
                return self.handle_auth_logout()
            if self.path == "/api/auth/change-password":
                return self.handle_change_password()
            if self.path == "/api/review-resume":
                return self.handle_review_resume()
            if self.path == "/api/rewrite-resume":
                return self.handle_resume_rewrite()
            if self.path == "/api/generate-resume-interview":
                return self.handle_resume_interview()
            if self.path == "/api/user-progress":
                return self.handle_update_user_progress()
            if self.path == "/api/user-progress/sync":
                return self.handle_sync_user_progress()
            return json_response(self, HTTPStatus.NOT_FOUND, {"ok": False, "error": "未找到对应接口"})
        except ValueError as exc:
            return json_response(self, HTTPStatus.BAD_REQUEST, {"ok": False, "error": str(exc)})
        except Exception as exc:
            return json_response(self, HTTPStatus.INTERNAL_SERVER_ERROR, {"ok": False, "error": f"服务器内部错误：{exc}"})

    def handle_auth_me(self):
        user, session_id = self.resolve_current_user()
        payload = {
            "ok": True,
            "authenticated": bool(user),
            "user": user,
            "policy": PASSWORD_POLICY,
        }
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        if session_id and not user:
            self.send_header("Set-Cookie", self.clear_auth_cookie())
        self.end_headers()
        self.wfile.write(body)

    def handle_auth_register(self):
        if SETTINGS.storage_mode != "sqlite":
            raise ValueError("注册功能需要启用 sqlite 存储模式")

        payload = self.parse_json_body()
        username = validate_username(str(payload.get("username", "")))
        password = validate_password(str(payload.get("password", "")))
        confirm_password = str(payload.get("confirmPassword", ""))
        if password != confirm_password:
            raise ValueError("涓ゆ杈撳叆鐨勫瘑鐮佷笉涓€鑷?")

        username_normalized = normalize_username(username)
        existing = get_user_by_username(SETTINGS.app_db_path, username_normalized)
        if existing:
            raise ValueError("用户名已存在，请换一个试试")

        password_hash, password_salt = hash_password(password)
        user = create_user(
            SETTINGS.app_db_path,
            user_id=new_user_id(),
            username=username,
            username_normalized=username_normalized,
            password_hash=password_hash,
            password_salt=password_salt,
            now_iso=now_iso(),
        )
        visitor_id, visitor_created = self.resolve_visitor_id()
        session_id = new_session_id()
        create_auth_session(
            SETTINGS.app_db_path,
            session_id=session_id,
            user_id=user["id"],
            expires_at=session_expires_at(),
            now_iso=now_iso(),
        )
        progress = merge_progress_into_user(SETTINGS.app_db_path, visitor_id, user["id"])

        body = json.dumps(
            {
                "ok": True,
                "message": "注册成功，已自动登录",
                "user": user,
                "progress": progress,
                "policy": PASSWORD_POLICY,
            },
            ensure_ascii=False,
        ).encode("utf-8")
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Set-Cookie", self.build_auth_cookie(session_id))
        if visitor_created:
            self.send_header("Set-Cookie", self.build_visitor_cookie(visitor_id))
        self.end_headers()
        self.wfile.write(body)

    def handle_auth_login(self):
        if SETTINGS.storage_mode != "sqlite":
            raise ValueError("登录功能需要启用 sqlite 存储模式")

        payload = self.parse_json_body()
        username = str(payload.get("username", "")).strip()
        password = str(payload.get("password", ""))
        if not username or not password:
            raise ValueError("请输入用户名和密码")

        username_normalized = normalize_username(username)
        user_record = get_user_by_username(SETTINGS.app_db_path, username_normalized)
        if not user_record or not verify_password(password, user_record["password_hash"], user_record["password_salt"]):
            raise ValueError("用户名或密码错误")

        user = {
            "id": user_record["id"],
            "username": user_record["username"],
            "createdAt": user_record["created_at"],
        }
        visitor_id, visitor_created = self.resolve_visitor_id()
        session_id = new_session_id()
        create_auth_session(
            SETTINGS.app_db_path,
            session_id=session_id,
            user_id=user["id"],
            expires_at=session_expires_at(),
            now_iso=now_iso(),
        )
        progress = merge_progress_into_user(SETTINGS.app_db_path, visitor_id, user["id"])

        body = json.dumps(
            {
                "ok": True,
                "message": "登录成功",
                "user": user,
                "progress": progress,
                "policy": PASSWORD_POLICY,
            },
            ensure_ascii=False,
        ).encode("utf-8")
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Set-Cookie", self.build_auth_cookie(session_id))
        if visitor_created:
            self.send_header("Set-Cookie", self.build_visitor_cookie(visitor_id))
        self.end_headers()
        self.wfile.write(body)

    def handle_auth_logout(self):
        session_id = self.get_auth_session_id()
        if SETTINGS.storage_mode == "sqlite" and session_id:
            delete_auth_session(SETTINGS.app_db_path, session_id)

        body = json.dumps({"ok": True, "message": "密码规则已获取", "policy": PASSWORD_POLICY}, ensure_ascii=False).encode("utf-8")
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Set-Cookie", self.clear_auth_cookie())
        self.end_headers()
        self.wfile.write(body)

    def handle_change_password(self):
        if SETTINGS.storage_mode != "sqlite":
            raise ValueError("修改密码需要启用 sqlite 存储模式")

        user = self.require_authenticated_user()
        payload = self.parse_json_body()
        current_password = str(payload.get("currentPassword", ""))
        new_password = validate_password(str(payload.get("newPassword", "")))
        confirm_password = str(payload.get("confirmPassword", ""))

        if new_password != confirm_password:
            raise ValueError("两次输入的新密码不一致")
        if current_password == new_password:
            raise ValueError("新密码不能与当前密码相同")

        user_record = get_user_auth_record_by_id(SETTINGS.app_db_path, user["id"])
        if not user_record:
            raise ValueError("当前账号不存在，请重新登录")
        if not verify_password(current_password, user_record["password_hash"], user_record["password_salt"]):
            raise ValueError("当前密码错误")

        password_hash, password_salt = hash_password(new_password)
        update_user_password(SETTINGS.app_db_path, user["id"], password_hash, password_salt)
        return json_response(self, HTTPStatus.OK, {"ok": True, "message": "密码修改成功"})

    def handle_account_overview(self):
        if SETTINGS.storage_mode != "sqlite":
            raise ValueError("个人中心需要启用 sqlite 存储模式")

        user = self.require_authenticated_user()
        overview = get_account_overview(SETTINGS.app_db_path, user["id"])
        overview["user"] = user
        overview["storageMode"] = SETTINGS.storage_mode
        return json_response(self, HTTPStatus.OK, overview)

    def handle_review_resume(self):
        print("[OfferGo] /api/review-resume requested", flush=True)
        form = self.parse_multipart_form()
        file_item = form["resume_file"] if "resume_file" in form else None
        target_role = form.getfirst("target_role", "").strip()
        target_stack = form.getfirst("target_stack", "").strip()
        target_jd = form.getfirst("target_jd", "").strip()
        selected_domain = form.getfirst("selected_domain", "").strip()

        if file_item is None or getattr(file_item, "file", None) is None:
            raise ValueError("请先上传简历文件")
        if not target_role:
            raise ValueError("璇峰～鍐欑洰鏍囧矖浣?")

        filename = Path(file_item.filename or "resume.txt").name
        file_bytes = file_item.file.read()
        if not file_bytes:
            raise ValueError("简历文件为空")

        resume_text = extract_resume_text(filename, file_bytes)
        if not resume_text.strip():
            raise ValueError("未能从简历中提取有效文本，请优先尝试 DOCX / TXT 格式")

        extracted = extract_resume_keywords(resume_text, target_stack, target_jd, target_role)
        review, mode_label, ai_error = review_resume(
            resume_text=resume_text,
            filename=filename,
            target_role=target_role,
            target_stack=target_stack,
            target_jd=target_jd,
            selected_domain=selected_domain,
            extracted_keywords=extracted,
        )

        resume_id = uuid.uuid4().hex
        review = review or fallback_review(
            resume_text=resume_text,
            filename=filename,
            target_role=target_role,
            target_stack=target_stack,
            target_jd=target_jd,
            selected_domain=selected_domain,
            extracted_keywords=extracted,
        )
        review["modeLabel"] = mode_label
        review["resumeId"] = resume_id
        review["keywordExtraction"] = extracted
        if ai_error:
            review["aiFallbackReason"] = ai_error
        RESUME_SESSIONS.save(
            resume_id,
            {
                "resume_text": resume_text,
                "filename": filename,
                "target_role": target_role,
                "target_stack": target_stack,
                "target_jd": target_jd,
                "selected_domain": selected_domain,
                "review": review,
                "mode_label": mode_label,
                "ai_error": ai_error,
                "keywords": extracted,
            },
        )

        return json_response(
            self,
            HTTPStatus.OK,
            {
                "ok": True,
                "message": f"评审完成，当前模式：{mode_label}" + (f"，AI 回退原因：{ai_error}" if ai_error else ""),
                "review": review,
            },
        )

    def handle_resume_rewrite(self):
        payload = self.parse_json_body()
        record = get_cached_resume(payload.get("resume_id"))
        rewrite = generate_resume_rewrite(record)
        return json_response(
            self,
            HTTPStatus.OK,
            {
                "ok": True,
                "message": "已生成针对岗位的简历改写建议",
                "rewrite": rewrite,
                "mode": record["mode_label"],
            },
        )

    def handle_resume_interview(self):
        payload = self.parse_json_body()
        record = get_cached_resume(payload.get("resume_id"))
        interview_pack = generate_resume_interview_questions(record)
        return json_response(
            self,
            HTTPStatus.OK,
            {
                "ok": True,
                "message": "已生成基于简历的模拟面试题",
                "interviewPack": interview_pack,
                "mode": record["mode_label"],
            },
        )

    def handle_get_user_progress(self):
        user, _session_id = self.resolve_current_user()
        visitor_id, created = self.resolve_visitor_id()
        if SETTINGS.storage_mode != "sqlite":
            payload = {"ok": True, "favorites": [], "mastered": [], "practice": {}, "storageMode": "local"}
        elif user:
            payload = get_user_progress_payload(SETTINGS.app_db_path, user_id=user["id"])
        else:
            payload = get_user_progress_payload(SETTINGS.app_db_path, visitor_id)

        payload["authenticated"] = bool(user)
        payload["user"] = user
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        if created and not user:
            self.send_header("Set-Cookie", self.build_visitor_cookie(visitor_id))
        self.end_headers()
        self.wfile.write(body)

    def handle_update_user_progress(self):
        payload = self.parse_json_body()
        question_id = str(payload.get("questionId", "")).strip()
        if not question_id:
            raise ValueError("questionId is required")

        user, _session_id = self.resolve_current_user()
        visitor_id, created = self.resolve_visitor_id()
        if SETTINGS.storage_mode != "sqlite":
            response = {"ok": True, "storageMode": "local"}
        else:
            favorite = payload["favorite"] if "favorite" in payload else None
            mastered = payload["mastered"] if "mastered" in payload else None
            practiced_at = current_timestamp() if payload.get("practiced") else None
            response = upsert_question_progress(
                SETTINGS.app_db_path,
                visitor_id,
                question_id,
                user_id=user["id"] if user else "",
                favorite=favorite,
                mastered=mastered,
                practiced_at=practiced_at,
            )

        body = json.dumps(response, ensure_ascii=False).encode("utf-8")
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        if created and not user:
            self.send_header("Set-Cookie", self.build_visitor_cookie(visitor_id))
        self.end_headers()
        self.wfile.write(body)

    def handle_sync_user_progress(self):
        payload = self.parse_json_body()
        user, _session_id = self.resolve_current_user()
        visitor_id, created = self.resolve_visitor_id()
        favorites = payload.get("favorites", [])
        mastered = payload.get("mastered", [])

        if SETTINGS.storage_mode != "sqlite":
            response = {"ok": True, "favorites": favorites, "mastered": mastered, "practice": {}, "storageMode": "local"}
        else:
            response = sync_user_progress(
                SETTINGS.app_db_path,
                visitor_id,
                [str(item) for item in favorites],
                [str(item) for item in mastered],
                user_id=user["id"] if user else "",
            )

        body = json.dumps(response, ensure_ascii=False).encode("utf-8")
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        if created and not user:
            self.send_header("Set-Cookie", self.build_visitor_cookie(visitor_id))
        self.end_headers()
        self.wfile.write(body)

    def parse_multipart_form(self):
        content_length = int(self.headers.get("Content-Length", "0"))
        if content_length <= 0:
            raise ValueError("璇锋眰浣撲负绌?")
        if content_length > SETTINGS.max_upload_size:
            raise ValueError("上传文件过大，请控制在 5MB 以内")
        content_type = self.headers.get("Content-Type", "")
        if "multipart/form-data" not in content_type:
            raise ValueError("璇锋眰鏍煎紡涓嶆纭紝闇€瑕?multipart/form-data")

        boundary_match = re.search(r'boundary="?([^";]+)"?', content_type)
        if not boundary_match:
            raise ValueError("无法解析上传边界信息")

        raw = self.rfile.read(content_length)
        boundary = ("--" + boundary_match.group(1)).encode("utf-8")
        form = SimpleForm()

        for part in raw.split(boundary):
            part = part.strip()
            if not part or part in {b"--", b""}:
                continue
            if part.endswith(b"--"):
                part = part[:-2]
            part = part.strip(b"\r\n")
            if not part:
                continue

            header_blob, separator, body = part.partition(b"\r\n\r\n")
            if not separator:
                continue

            headers = header_blob.decode("utf-8", errors="ignore")
            disposition_match = re.search(r'name="([^"]+)"', headers)
            if not disposition_match:
                continue
            field_name = disposition_match.group(1)

            body = body.rstrip(b"\r\n")
            filename_match = re.search(r'filename="([^"]*)"', headers)
            if filename_match:
                filename = Path(filename_match.group(1) or "upload.bin").name
                form[field_name] = UploadedFile(filename, body)
            else:
                form[field_name] = body.decode("utf-8", errors="ignore")

        return form

    def parse_json_body(self):
        content_length = int(self.headers.get("Content-Length", "0"))
        if content_length <= 0:
            raise ValueError("璇锋眰浣撲负绌?")
        raw = self.rfile.read(content_length).decode("utf-8")
        return json.loads(raw)

    def log_message(self, format, *args):
        sys.stdout.write("%s - - [%s] %s\n" % (self.address_string(), self.log_date_time_string(), format % args))
        sys.stdout.flush()

    def serve_tracked_index(self):
        visitor_id = self.ensure_visitor_cookie()
        user_agent = self.headers.get("User-Agent", "")
        VISITOR_TRACKER.track_visit(visitor_id, "/web_mvp/", user_agent=user_agent)

        index_path = WEB_DIR / "index.html"
        body = index_path.read_bytes()
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Set-Cookie", self.build_visitor_cookie(visitor_id))
        self.end_headers()
        self.wfile.write(body)

    def ensure_visitor_cookie(self):
        cookie_header = self.headers.get("Cookie", "")
        if cookie_header:
            cookie = SimpleCookie()
            cookie.load(cookie_header)
            morsel = cookie.get(SETTINGS.visitor_cookie_name)
            if morsel and morsel.value:
                return morsel.value
        return uuid.uuid4().hex

    def resolve_visitor_id(self):
        cookie_header = self.headers.get("Cookie", "")
        if cookie_header:
            cookie = SimpleCookie()
            cookie.load(cookie_header)
            morsel = cookie.get(SETTINGS.visitor_cookie_name)
            if morsel and morsel.value:
                return morsel.value, False
        return uuid.uuid4().hex, True

    def build_visitor_cookie(self, visitor_id):
        max_age = 60 * 60 * 24 * 365
        return f"{SETTINGS.visitor_cookie_name}={visitor_id}; Path=/; Max-Age={max_age}; SameSite=Lax"

    def get_auth_session_id(self):
        cookie_header = self.headers.get("Cookie", "")
        if not cookie_header:
            return ""
        cookie = SimpleCookie()
        cookie.load(cookie_header)
        morsel = cookie.get(AUTH_COOKIE_NAME)
        return morsel.value if morsel and morsel.value else ""

    def resolve_current_user(self):
        if SETTINGS.storage_mode != "sqlite":
            return None, ""
        session_id = self.get_auth_session_id()
        if not session_id:
            return None, ""
        return get_auth_session_user(SETTINGS.app_db_path, session_id, now_iso()), session_id

    def require_authenticated_user(self):
        user, _session_id = self.resolve_current_user()
        if not user:
            raise ValueError("请先登录后再继续操作")
        return user

    def build_auth_cookie(self, session_id):
        return f"{AUTH_COOKIE_NAME}={session_id}; Path=/; Max-Age={SESSION_MAX_AGE_SECONDS}; HttpOnly; SameSite=Lax"

    def clear_auth_cookie(self):
        return f"{AUTH_COOKIE_NAME}=; Path=/; Max-Age=0; HttpOnly; SameSite=Lax"


def get_cached_resume(resume_id):
    record = RESUME_SESSIONS.get(resume_id)
    if not resume_id or record is None:
        raise ValueError("当前简历会话已失效，请重新上传并评审")
    return record


def extract_resume_text(filename, data):
    suffix = Path(filename).suffix.lower()
    if suffix in {".txt", ".md"}:
        return decode_text_bytes(data)
    if suffix == ".docx":
        return extract_docx_text(data)
    if suffix == ".pdf":
        return extract_pdf_text(data)
    raise ValueError("暂不支持该文件格式，请上传 PDF / DOCX / TXT / MD")


def decode_text_bytes(data):
    for encoding in ("utf-8", "utf-8-sig", "gb18030", "gbk"):
        try:
            return data.decode(encoding)
        except UnicodeDecodeError:
            continue
    return data.decode("utf-8", errors="ignore")


def extract_docx_text(data):
    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        try:
            document_xml = archive.read("word/document.xml")
        except KeyError as exc:
            raise ValueError("DOCX 文件结构异常，无法读取正文") from exc

    root = ET.fromstring(document_xml)
    namespace = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
    paragraphs = []
    for paragraph in root.findall(".//w:p", namespace):
        texts = [node.text for node in paragraph.findall(".//w:t", namespace) if node.text]
        line = "".join(texts).strip()
        if line:
            paragraphs.append(line)
    return "\n".join(paragraphs)


def extract_pdf_text(data):
    try:
        from pypdf import PdfReader
    except Exception as exc:
        raise ValueError("当前 Python 环境没有安装 pypdf，建议先用 DOCX / TXT，或者安装 pypdf 后再试 PDF") from exc

    reader = PdfReader(io.BytesIO(data))
    parts = []
    for page in reader.pages:
        text = (page.extract_text() or "").strip()
        if text:
            parts.append(text)
    return "\n".join(parts)


def split_keywords(*texts):
    tokens = []
    for text in texts:
        if not text:
            continue
        for piece in re.split(r"[,\n，。；;、|()\[\]\s]+", str(text)):
            clean = piece.strip()
            if len(clean) >= 2:
                tokens.append(clean)
    ordered = []
    seen = set()
    for token in tokens:
        key = token.lower()
        if key not in seen:
            seen.add(key)
            ordered.append(token)
    return ordered[:25]


def extract_resume_keywords(resume_text, target_stack, target_jd, target_role):
    source = "\n".join([resume_text, target_stack, target_jd, target_role]).lower()
    matched = [keyword for keyword in COMMON_TECH_KEYWORDS if keyword.lower() in source]
    resume_keywords = [keyword for keyword in COMMON_TECH_KEYWORDS if keyword.lower() in resume_text.lower()]

    custom_keywords = split_keywords(target_stack, target_jd, target_role)
    resume_lines = [line.strip() for line in resume_text.splitlines() if line.strip()]
    experience_signals = []
    for line in resume_lines:
        if any(token in line for token in ["负责", "实现", "优化", "项目", "实习", "设计", "搭建", "上线"]):
            experience_signals.append(line[:120])
        if len(experience_signals) >= 6:
            break

    return {
        "targetKeywords": custom_keywords[:15],
        "detectedTechKeywords": matched[:15],
        "resumeTechKeywords": resume_keywords[:15],
        "experienceSignals": experience_signals,
    }


def review_resume(resume_text, filename, target_role, target_stack, target_jd, selected_domain, extracted_keywords):
    llm_config = resolve_resume_llm_config()
    api_key = llm_config["api_key"]
    if api_key:
        try:
            print(
                f"[OfferGo] Starting resume review LLM call: file={filename}, role={target_role}, domain={selected_domain or 'all'}, model={llm_config['model']}",
                flush=True,
            )
            review = call_llm_review(
                api_key=api_key,
                api_url=llm_config["api_url"],
                model=llm_config["model"],
                max_tokens=llm_config["max_tokens"],
                resume_text=resume_text,
                filename=filename,
                target_role=target_role,
                target_stack=target_stack,
                target_jd=target_jd,
                selected_domain=selected_domain,
                extracted_keywords=extracted_keywords,
            )
            print("[OfferGo] Resume review LLM succeeded.", flush=True)
            return review, "AI 模型版", ""
        except Exception as exc:
            error_message = str(exc).strip() or exc.__class__.__name__
            print(f"[OfferGo] Resume review LLM failed: {error_message}", file=sys.stderr, flush=True)
            traceback.print_exc()
            return None, "AI 调用失败，已切换本地规则版", error_message

    review = fallback_review(
        resume_text=resume_text,
        filename=filename,
        target_role=target_role,
        target_stack=target_stack,
        target_jd=target_jd,
        selected_domain=selected_domain,
        extracted_keywords=extracted_keywords,
    )
    return review, "本地规则版", ""

def build_prompt(name, **kwargs):
    template = PROMPTS[name]
    return template.format(**kwargs)


def call_deepseek_json(api_key, api_url, model, max_tokens, system_prompt, user_prompt):
    payload = {
        "model": model,
        "temperature": 0.2,
        "max_tokens": max_tokens,
        "response_format": {"type": "json_object"},
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
    }

    request = urllib.request.Request(
        api_url,
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        },
        method="POST",
    )

    try:
        print(f"[OfferGo] POST {api_url}", flush=True)
        # Avoid inheriting any broken system proxy settings such as 127.0.0.1:9.
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
        with opener.open(request, timeout=90) as response:
            result = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="ignore")
        raise ValueError(f"大模型接口调用失败：HTTP {exc.code} {detail}") from exc
    except urllib.error.URLError as exc:
        raise ValueError(f"大模型接口网络不可达：{exc.reason}") from exc

    content = result["choices"][0]["message"]["content"]
    return safe_parse_json(content)


def call_llm_review(api_key, api_url, model, max_tokens, resume_text, filename, target_role, target_stack, target_jd, selected_domain, extracted_keywords):
    parsed = call_deepseek_json(
        api_key=api_key,
        api_url=api_url,
        model=model,
        max_tokens=max_tokens,
        system_prompt=PROMPTS["review_system"],
        user_prompt=build_prompt(
            "review_user",
            target_role=target_role,
            selected_domain=selected_domain or "鏈寚瀹?",
            target_stack=target_stack or "鏈彁渚?",
            target_jd=target_jd or "鏈彁渚?",
            filename=filename,
            extracted_keywords=json.dumps(extracted_keywords, ensure_ascii=False),
            resume_text=resume_text[:18000],
        )
        + STRUCTURED_OUTPUT_HINT,
    )
    if not isinstance(parsed, dict):
        raise ValueError("大模型返回的不是有效 JSON")
    return normalize_review(parsed, target_role)


def generate_resume_rewrite(record):
    llm_config = resolve_resume_llm_config()
    api_key = llm_config["api_key"]
    if api_key:
        try:
            parsed = call_deepseek_json(
                api_key=api_key,
                api_url=llm_config["api_url"],
                model=llm_config["model"],
                max_tokens=llm_config["max_tokens"],
                system_prompt=PROMPTS["rewrite_system"],
                user_prompt=build_prompt(
                    "rewrite_user",
                    target_role=record["target_role"],
                    target_stack=record["target_stack"] or "鏈彁渚?",
                    target_jd=record["target_jd"] or "鏈彁渚?",
                    review=json.dumps(record["review"], ensure_ascii=False),
                    resume_text=record["resume_text"][:18000],
                )
                + STRUCTURED_OUTPUT_HINT,
            )
            return normalize_rewrite(parsed)
        except Exception as exc:
            print(f"[OfferGo] Resume rewrite LLM failed: {str(exc).strip() or exc.__class__.__name__}", file=sys.stderr, flush=True)
    return fallback_rewrite(record)


def generate_resume_interview_questions(record):
    llm_config = resolve_resume_llm_config()
    api_key = llm_config["api_key"]
    if api_key:
        try:
            parsed = call_deepseek_json(
                api_key=api_key,
                api_url=llm_config["api_url"],
                model=llm_config["model"],
                max_tokens=llm_config["max_tokens"],
                system_prompt=PROMPTS["interview_system"],
                user_prompt=build_prompt(
                    "interview_user",
                    target_role=record["target_role"],
                    target_stack=record["target_stack"] or "鏈彁渚?",
                    target_jd=record["target_jd"] or "鏈彁渚?",
                    review=json.dumps(record["review"], ensure_ascii=False),
                    resume_text=record["resume_text"][:18000],
                )
                + STRUCTURED_OUTPUT_HINT,
            )
            return normalize_interview_pack(parsed)
        except Exception as exc:
            print(f"[OfferGo] Resume interview LLM failed: {str(exc).strip() or exc.__class__.__name__}", file=sys.stderr, flush=True)
    return fallback_interview_pack(record)


def safe_parse_json(text):
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", text, flags=re.S)
        if match:
            return json.loads(match.group(0))
        raise


def fallback_review(resume_text, filename, target_role, target_stack, target_jd, selected_domain, extracted_keywords):
    lowered = resume_text.lower()
    keywords = split_keywords(target_stack, target_jd, target_role, selected_domain)
    matched = [keyword for keyword in keywords if keyword.lower() in lowered]
    missing = [keyword for keyword in keywords if keyword.lower() not in lowered]

    dimension_scores = [
        score_dimension("技术栈", has_keywords(resume_text, COMMON_TECH_KEYWORDS), has_keywords(resume_text, matched), "技术关键词覆盖情况"),
        score_dimension("项目经历", section_signal(resume_text, ["项目", "经历", "负责"]), count_project_signals(resume_text), "项目描述展开情况"),
        score_dimension("实习经历", section_signal(resume_text, ["实习", "实训", "校招"]), count_project_signals(resume_text, internship=True), "实习经历展示情况"),
        score_dimension("学历背景", section_signal(resume_text, ["本科", "硕士", "博士", "学校", "院校", "专业"]), count_education_signals(resume_text), "教育背景展示情况"),
        score_dimension("科研经历", section_signal(resume_text, ["科研", "论文", "实验", "竞赛", "课题"]), count_research_signals(resume_text), "科研内容展示情况"),
        score_dimension("岗位匹配度", max(len(keywords), 1), len(matched), "目标岗位关键词匹配情况"),
        score_dimension("表达质量", max(len(resume_text) // 600, 1), count_bullet_signals(resume_text), "条理化表达情况"),
    ]

    overall = int(sum(item["score"] for item in dimension_scores) / len(dimension_scores))
    review = {
        "overallScore": overall,
        "summary": build_summary(overall, target_role, matched, missing),
        "dimensionScores": dimension_scores,
        "jobMatch": {
            "targetRole": target_role,
            "matchScore": clamp_score(40 + len(matched) * 8 - len(missing) * 3),
            "reasoning": build_match_reasoning(matched, missing, target_jd),
            "matchedKeywords": matched[:10],
            "missingKeywords": missing[:10],
        },
        "highlights": build_highlights(resume_text, matched),
        "risks": build_risks(resume_text, missing),
        "suggestions": build_suggestions(resume_text, missing),
        "rewrittenBullets": build_rewritten_bullets(target_role, matched),
        "fileName": filename,
        "keywordExtraction": extracted_keywords,
    }
    return normalize_review(review, target_role)


def fallback_rewrite(record):
    matched = record["review"]["jobMatch"].get("matchedKeywords", [])
    missing = record["review"]["jobMatch"].get("missingKeywords", [])
    role = record["target_role"]
    target_stack = record["target_stack"] or "未填写"
    return normalize_rewrite(
        {
            "headline": f"面向 {role} 的简历改写建议",
            "summaryRewrite": f"针对 {role} 岗位和 {target_stack} 技术栈，可把项目和经历写得更具体一些，突出结果、职责和技术关键词。",
            "skillsRewrite": [
                "把技术栈按“熟练 / 掌握 / 了解”分层写清楚，避免只堆关键词：" + ((", ".join(matched[:6])) or target_stack) + "。",
                "优先补充和岗位最相关的技术关键词、工具和业务场景。",
            ],
            "projectRewrite": build_rewritten_bullets(role, matched),
            "experienceRewrite": [
                "每段经历尽量写清楚：背景、你的职责、具体动作、结果指标。",
                "如果有成果，尽量补数字，比如性能提升、转化率、节省时间等。",
            ],
            "educationRewrite": [
                "教育经历可以补充专业方向、核心课程和项目关联性。",
                "如果有竞赛、科研或实验室经历，也可以补到这一部分。",
            ],
            "missingKeywordsAdvice": missing[:10],
        }
    )

def fallback_interview_pack(record):
    role = record["target_role"]
    matched = record["review"]["jobMatch"].get("matchedKeywords", [])
    missing = record["review"]["jobMatch"].get("missingKeywords", [])
    top_keyword = matched[0] if matched else (missing[0] if missing else "暂无关键词")
    questions = [
        {
            "question": f"请结合你的简历，介绍一下你为什么适合 {role} 这个岗位？",
            "intent": "考察你对岗位要求和个人经历的匹配理解",
            "answerTips": ["对齐岗位要求", "结合简历中的项目或经历", "说明你的优势和补足方向"],
        },
        {
            "question": f"你在简历里提到的 {top_keyword}，能展开讲讲你的实际贡献吗？",
            "intent": "考察关键词背后的真实经历和深度",
            "answerTips": ["说清楚具体做了什么", "解释你的技术选择", "补充结果和影响"],
        },
        {
            "question": "如果让你重新做一次这段项目经历，你会怎么优化？",
            "intent": "考察复盘能力和成长意识",
            "answerTips": ["讲优化思路", "讲取舍", "讲结果提升空间"],
        },
        {
            "question": "你会如何把简历中的内容改得更贴合岗位 JD？",
            "intent": "考察岗位匹配意识",
            "answerTips": ["找出关键词", "补充相关经历", "删掉不相关内容"],
        },
    ]
    follow_ups = [
        f"你在 {top_keyword} 这部分有没有量化结果或业务收益？",
        f"如果面试官继续追问 {role} 岗位相关技术，你怎么接？",
        "这段经历里最难的一点是什么，你怎么解决的？",
    ]
    if missing:
        questions.append(
            {
                "question": f"简历里还没有明显体现 {missing[0]}，如果面试官问到你会怎么补充？",
                "intent": "考察补强能力与表达策略",
                "answerTips": ["说明已有经验", "补充学习或项目计划", "把空缺转成成长方向"],
            }
        )
        follow_ups.append(f"如果岗位强依赖 {missing[0]}，你打算怎么在短期内补齐？")
    return normalize_interview_pack(
        {
            "headline": "基于简历的模拟面试题",
            "questions": questions,
            "followUps": follow_ups,
        }
    )

    tokens = []
    for text in texts:
        if not text:
            continue
        for piece in re.split(r"[,\n锛屻€?锛?|()\[\]锛?\s]+", text):
            clean = piece.strip()
            if len(clean) >= 2:
                tokens.append(clean)
    ordered = []
    seen = set()
    for token in tokens:
        key = token.lower()
        if key not in seen:
            seen.add(key)
            ordered.append(token)
    return ordered[:25]


def has_keywords(text, keywords):
    lowered = text.lower()
    return sum(1 for keyword in keywords if keyword.lower() in lowered)


def section_signal(text, markers):
    lowered = text.lower()
    return sum(1 for marker in markers if marker.lower() in lowered)


def count_project_signals(text, internship=False):
    markers = ["负责", "实现", "优化", "设计", "落地", "性能", "并发", "接口", "系统", "业务"]
    if internship:
        markers.extend(["实习", "上线", "团队", "协作"])
    return has_keywords(text, markers)


def count_education_signals(text):
    return has_keywords(text, ["本科", "硕士", "博士", "大学", "学院", "专业", "绩点", "排名"])


def count_research_signals(text):
    return has_keywords(text, ["科研", "论文", "实验", "课题", "竞赛", "专利", "研究"])


def count_bullet_signals(text):
    return text.count("?") + text.count("-") + text.count("1.") + text.count("2.") + text.count("3.")

def score_dimension(name, total_signal, positive_signal, reasoning_label):
    if total_signal <= 0:
        score = 35
        verdict = "不足"
        reasoning = f"简历中尚未看到足够的{name}信息，建议补充{reasoning_label}。"
    else:
        ratio = positive_signal / max(total_signal, 1)
        score = clamp_score(int(45 + ratio * 45 + min(positive_signal, 5) * 3))
        if score >= 80:
            verdict = "表现较强"
        elif score >= 65:
            verdict = "较为完整"
        elif score >= 50:
            verdict = "需要补强"
        else:
            verdict = "明显不足"
        reasoning = f"{name}维度识别到 {positive_signal} 个有效信号，{reasoning_label} 仍有提升空间。"
    return {"name": name, "score": score, "verdict": verdict, "reasoning": reasoning}


def clamp_score(value):
    return max(0, min(100, int(value)))


def build_summary(overall, target_role, matched, missing):
    if overall >= 80:
        prefix = "整体表现不错，"
    elif overall >= 65:
        prefix = "整体处于中等水平，"
    else:
        prefix = "整体匹配度偏低，"
    matched_text = "、".join(matched[:5]) if matched else "暂无明显匹配项"
    missing_text = "、".join(missing[:5]) if missing else "暂无明显缺失项"
    return f"{prefix}当前简历与 {target_role} 岗位的匹配重点在 {matched_text}；建议优先补足 {missing_text}。"


def build_match_reasoning(matched, missing, target_jd):
    if matched and not missing:
        return "已经覆盖了较多目标关键词，但仍建议结合岗位 JD 再补充细节。"
    if matched:
        return f"已匹配 {len(matched)} 个目标关键词，仍有 {len(missing)} 个关键词未覆盖，建议继续贴合 JD 优化。"
    if target_jd:
        return "已结合 JD 做基础判断，但简历与目标岗位的关键词匹配仍然偏少。"
    return "当前简历缺少足够的岗位信息，建议补充经历与成果后再评审。"


def build_highlights(resume_text, matched):
    highlights = []
    if matched:
        highlights.append("简历中已体现：" + "、".join(matched[:6]) + "。")
    if section_signal(resume_text, ["项目", "经历", "负责"]):
        highlights.append("项目/经历部分比较完整，说明你有一定的实战表达基础。")
    if section_signal(resume_text, ["实习", "校招"]):
        highlights.append("简历里有实习或校招相关信息，和岗位衔接更自然。")
    if section_signal(resume_text, ["本科", "硕士", "博士", "学校", "专业"]):
        highlights.append("教育背景信息较完整，方便快速判断基础能力。")
    return highlights or ["简历中可直接用于岗位判断的信息还不够多。"]


def build_risks(resume_text, missing):
    risks = []
    if missing:
        risks.append("目标岗位关键词缺失：" + "、".join(missing[:6]) + "。")
    if not section_signal(resume_text, ["负责", "%", "提升", "优化", "增长", "减少"]):
        risks.append("缺少量化结果，简历说服力会偏弱。")
    if not section_signal(resume_text, ["项目", "经历"]):
        risks.append("项目/实习经历展示不够清晰，可能影响岗位匹配判断。")
    if not section_signal(resume_text, ["本科", "硕士", "博士", "学校"]):
        risks.append("学历或教育背景信息不够完整，建议补充。")
    return risks[:6]


def build_suggestions(resume_text, missing):
    suggestions = [
        "把技术栈按“熟练 / 掌握 / 了解”三层写法整理清楚。",
        "每段项目经历补上业务背景、你的职责、技术方案和结果。",
        "优先把和目标岗位最近的项目放到最前面。",
        "尽量写出具体数字，比如性能提升、效率提升、用户增长等。",
        "如果有实习/项目协作经历，也要写清楚你在团队中的角色。",
    ]
    if missing:
        suggestions.append("重点补足：" + "、".join(missing[:8]) + "。")
    if not section_signal(resume_text, ["项目", "经历", "负责"]):
        suggestions.append("建议增加项目或实战经历，让岗位匹配更直观。")
    return suggestions[:10]


def build_rewritten_bullets(target_role, matched):
    matched_text = "、".join(matched[:4]) if matched else "岗位关键能力"
    return [
        f"围绕 {matched_text} 这些关键词，把与 {target_role} 岗位相关的项目和职责写得更具体。",
        "每段经历尽量用“背景 - 行动 - 结果”结构来写。",
        "如果有技术方案，补上为什么这么做，以及带来了什么收益。",
        "没有现成成果时，也可以写学习过程和迭代过程，但要写得具体。",
    ]


def normalize_review(review, target_role):
    review.setdefault("overallScore", 0)
    review.setdefault("summary", "")
    review.setdefault("dimensionScores", [])
    review.setdefault("jobMatch", {})
    review.setdefault("highlights", [])
    review.setdefault("risks", [])
    review.setdefault("suggestions", [])
    review.setdefault("rewrittenBullets", [])
    review.setdefault("keywordExtraction", {})

    review["overallScore"] = clamp_score(review["overallScore"])
    review["jobMatch"].setdefault("targetRole", target_role)
    review["jobMatch"]["matchScore"] = clamp_score(review["jobMatch"].get("matchScore", 0))
    review["jobMatch"]["matchedKeywords"] = list(review["jobMatch"].get("matchedKeywords", []))[:10]
    review["jobMatch"]["missingKeywords"] = list(review["jobMatch"].get("missingKeywords", []))[:10]

    dimensions = []
    for item in review["dimensionScores"]:
        if isinstance(item, dict):
            dimensions.append(
                {
                    "name": str(item.get("name", "")),
                    "score": clamp_score(item.get("score", 0)),
                    "verdict": str(item.get("verdict", "")),
                    "reasoning": str(item.get("reasoning", "")),
                }
            )
    review["dimensionScores"] = dimensions
    return review


def normalize_rewrite(payload):
    payload = payload if isinstance(payload, dict) else {}
    return {
        "headline": str(payload.get("headline", "简历改写建议")),
        "summaryRewrite": str(payload.get("summaryRewrite", "")),
        "skillsRewrite": list(payload.get("skillsRewrite", []))[:10],
        "projectRewrite": list(payload.get("projectRewrite", []))[:10],
        "experienceRewrite": list(payload.get("experienceRewrite", []))[:10],
        "educationRewrite": list(payload.get("educationRewrite", []))[:10],
        "missingKeywordsAdvice": list(payload.get("missingKeywordsAdvice", []))[:10],
    }


def normalize_interview_pack(payload):
    payload = payload if isinstance(payload, dict) else {}
    questions = []
    for item in payload.get("questions", []):
        if isinstance(item, dict):
            questions.append(
                {
                    "question": str(item.get("question", "")),
                    "intent": str(item.get("intent", "")),
                    "answerTips": list(item.get("answerTips", []))[:6],
                }
            )
        elif isinstance(item, str) and item.strip():
            questions.append({"question": item.strip(), "intent": "", "answerTips": []})

    follow_ups = []
    for item in payload.get("followUps", []):
        if isinstance(item, dict):
            text = item.get("question") or item.get("text") or item.get("content") or item.get("title") or ""
        else:
            text = str(item)
        text = str(text).strip()
        if text:
            follow_ups.append(text)
    return {
        "headline": str(payload.get("headline", "基于简历的模拟面试题")),
        "questions": questions[:12],
        "followUps": follow_ups[:12],
    }

def main():
    if SETTINGS.storage_mode == "sqlite":
        initialize_database(SETTINGS.app_db_path)
        ensure_questions_seeded(SETTINGS.app_db_path, WEB_DIR / "data" / "questions.json")
    server = ThreadingHTTPServer((SETTINGS.host, SETTINGS.port), ResumeReviewHandler)
    print(f"Resume review server running at http://{SETTINGS.host}:{SETTINGS.port}/web_mvp/")
    print(f"API health: http://{SETTINGS.host}:{SETTINGS.port}/api/health")
    print(f"Storage mode: {SETTINGS.storage_mode}")
    server.serve_forever()


if __name__ == "__main__":
    main()

