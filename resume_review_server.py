import io
import json
import os
import re
import sys
import urllib.error
import urllib.request
import uuid
import zipfile
from http import HTTPStatus
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs
from xml.etree import ElementTree as ET


ROOT = Path(__file__).resolve().parent
HOST = os.environ.get("RESUME_REVIEW_HOST", "0.0.0.0")
PORT = int(os.environ.get("RESUME_REVIEW_PORT", "8000"))
MAX_UPLOAD_SIZE = 5 * 1024 * 1024
DEEPSEEK_API_URL = "https://api.deepseek.com/chat/completions"
PROMPT_FILE = ROOT / "prompt_templates.json"

RESUME_CACHE = {}

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


def json_response(handler, status, payload):
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    handler.send_response(status)
    handler.send_header("Content-Type", "application/json; charset=utf-8")
    handler.send_header("Content-Length", str(len(body)))
    handler.end_headers()
    handler.wfile.write(body)


class ResumeReviewHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(ROOT), **kwargs)

    def do_GET(self):
        if self.path in {"/", ""}:
            self.send_response(HTTPStatus.FOUND)
            self.send_header("Location", "/web_mvp/")
            self.end_headers()
            return
        if self.path == "/api/health":
            return json_response(self, HTTPStatus.OK, {"ok": True, "service": "resume-review"})
        return super().do_GET()

    def do_POST(self):
        try:
            if self.path == "/api/review-resume":
                return self.handle_review_resume()
            if self.path == "/api/rewrite-resume":
                return self.handle_resume_rewrite()
            if self.path == "/api/generate-resume-interview":
                return self.handle_resume_interview()
            return json_response(self, HTTPStatus.NOT_FOUND, {"ok": False, "error": "接口不存在"})
        except ValueError as exc:
            return json_response(self, HTTPStatus.BAD_REQUEST, {"ok": False, "error": str(exc)})
        except Exception as exc:
            return json_response(self, HTTPStatus.INTERNAL_SERVER_ERROR, {"ok": False, "error": f"服务异常：{exc}"})

    def handle_review_resume(self):
        form = self.parse_multipart_form()
        file_item = form["resume_file"] if "resume_file" in form else None
        target_role = form.getfirst("target_role", "").strip()
        target_stack = form.getfirst("target_stack", "").strip()
        target_jd = form.getfirst("target_jd", "").strip()
        selected_domain = form.getfirst("selected_domain", "").strip()

        if file_item is None or getattr(file_item, "file", None) is None:
            raise ValueError("请先上传简历文件")
        if not target_role:
            raise ValueError("请填写目标岗位")

        filename = Path(file_item.filename or "resume.txt").name
        file_bytes = file_item.file.read()
        if not file_bytes:
            raise ValueError("简历文件为空")

        resume_text = extract_resume_text(filename, file_bytes)
        if not resume_text.strip():
            raise ValueError("未能从简历中提取有效文本，请优先尝试 DOCX / TXT 格式")

        extracted = extract_resume_keywords(resume_text, target_stack, target_jd, target_role)
        review, mode_label = review_resume(
            resume_text=resume_text,
            filename=filename,
            target_role=target_role,
            target_stack=target_stack,
            target_jd=target_jd,
            selected_domain=selected_domain,
            extracted_keywords=extracted,
        )

        resume_id = uuid.uuid4().hex
        review["modeLabel"] = mode_label
        review["resumeId"] = resume_id
        review["keywordExtraction"] = extracted
        RESUME_CACHE[resume_id] = {
            "resume_text": resume_text,
            "filename": filename,
            "target_role": target_role,
            "target_stack": target_stack,
            "target_jd": target_jd,
            "selected_domain": selected_domain,
            "review": review,
            "mode_label": mode_label,
            "keywords": extracted,
        }

        return json_response(
            self,
            HTTPStatus.OK,
            {
                "ok": True,
                "message": f"评审完成，当前模式：{mode_label}",
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

    def parse_multipart_form(self):
        content_length = int(self.headers.get("Content-Length", "0"))
        if content_length <= 0:
            raise ValueError("请求体为空")
        if content_length > MAX_UPLOAD_SIZE:
            raise ValueError("上传文件过大，请控制在 5MB 以内")
        content_type = self.headers.get("Content-Type", "")
        if "multipart/form-data" not in content_type:
            raise ValueError("请求格式不正确，需要 multipart/form-data")

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
            raise ValueError("请求体为空")
        raw = self.rfile.read(content_length).decode("utf-8")
        return json.loads(raw)

    def log_message(self, format, *args):
        sys.stdout.write("%s - - [%s] %s\n" % (self.address_string(), self.log_date_time_string(), format % args))


def get_cached_resume(resume_id):
    if not resume_id or resume_id not in RESUME_CACHE:
        raise ValueError("当前简历会话已失效，请重新上传并评审")
    return RESUME_CACHE[resume_id]


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
        raise ValueError("当前 Python 环境没有安装 pypdf，建议先用 DOCX / TXT，或安装 pypdf 后再试 PDF") from exc

    reader = PdfReader(io.BytesIO(data))
    parts = []
    for page in reader.pages:
        text = (page.extract_text() or "").strip()
        if text:
            parts.append(text)
    return "\n".join(parts)


def extract_resume_keywords(resume_text, target_stack, target_jd, target_role):
    source = "\n".join([resume_text, target_stack, target_jd, target_role]).lower()
    matched = [keyword for keyword in COMMON_TECH_KEYWORDS if keyword.lower() in source]

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
        "experienceSignals": experience_signals,
    }


def review_resume(resume_text, filename, target_role, target_stack, target_jd, selected_domain, extracted_keywords):
    api_key = os.environ.get("DEEPSEEK_API_KEY", "").strip()
    if api_key:
        try:
            review = call_llm_review(
                api_key=api_key,
                resume_text=resume_text,
                filename=filename,
                target_role=target_role,
                target_stack=target_stack,
                target_jd=target_jd,
                selected_domain=selected_domain,
                extracted_keywords=extracted_keywords,
            )
            return review, "大模型评审"
        except Exception:
            pass

    review = fallback_review(
        resume_text=resume_text,
        filename=filename,
        target_role=target_role,
        target_stack=target_stack,
        target_jd=target_jd,
        selected_domain=selected_domain,
        extracted_keywords=extracted_keywords,
    )
    return review, "本地规则评审"


def build_prompt(name, **kwargs):
    template = PROMPTS[name]
    return template.format(**kwargs)


def call_deepseek_json(api_key, system_prompt, user_prompt):
    payload = {
        "model": os.environ.get("DEEPSEEK_MODEL", "deepseek-chat"),
        "temperature": 0.2,
        "response_format": {"type": "json_object"},
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
    }

    request = urllib.request.Request(
        DEEPSEEK_API_URL,
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(request, timeout=90) as response:
            result = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="ignore")
        raise ValueError(f"大模型接口调用失败：HTTP {exc.code} {detail}") from exc

    content = result["choices"][0]["message"]["content"]
    return safe_parse_json(content)


def call_llm_review(api_key, resume_text, filename, target_role, target_stack, target_jd, selected_domain, extracted_keywords):
    parsed = call_deepseek_json(
        api_key=api_key,
        system_prompt=PROMPTS["review_system"],
        user_prompt=build_prompt(
            "review_user",
            target_role=target_role,
            selected_domain=selected_domain or "未指定",
            target_stack=target_stack or "未提供",
            target_jd=target_jd or "未提供",
            filename=filename,
            extracted_keywords=json.dumps(extracted_keywords, ensure_ascii=False),
            resume_text=resume_text[:18000],
        ),
    )
    if not isinstance(parsed, dict):
        raise ValueError("大模型返回的不是有效 JSON")
    return normalize_review(parsed, target_role)


def generate_resume_rewrite(record):
    api_key = os.environ.get("DEEPSEEK_API_KEY", "").strip()
    if api_key:
        try:
            parsed = call_deepseek_json(
                api_key=api_key,
                system_prompt=PROMPTS["rewrite_system"],
                user_prompt=build_prompt(
                    "rewrite_user",
                    target_role=record["target_role"],
                    target_stack=record["target_stack"] or "未提供",
                    target_jd=record["target_jd"] or "未提供",
                    review=json.dumps(record["review"], ensure_ascii=False),
                    resume_text=record["resume_text"][:18000],
                ),
            )
            return normalize_rewrite(parsed)
        except Exception:
            pass
    return fallback_rewrite(record)


def generate_resume_interview_questions(record):
    api_key = os.environ.get("DEEPSEEK_API_KEY", "").strip()
    if api_key:
        try:
            parsed = call_deepseek_json(
                api_key=api_key,
                system_prompt=PROMPTS["interview_system"],
                user_prompt=build_prompt(
                    "interview_user",
                    target_role=record["target_role"],
                    target_stack=record["target_stack"] or "未提供",
                    target_jd=record["target_jd"] or "未提供",
                    review=json.dumps(record["review"], ensure_ascii=False),
                    resume_text=record["resume_text"][:18000],
                ),
            )
            return normalize_interview_pack(parsed)
        except Exception:
            pass
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
        score_dimension("技术栈", has_keywords(resume_text, COMMON_TECH_KEYWORDS), has_keywords(resume_text, matched), "核心技术栈覆盖情况"),
        score_dimension("项目经历", section_signal(resume_text, ["项目", "项目经历", "项目经验"]), count_project_signals(resume_text), "项目是否具体、是否有产出"),
        score_dimension("实习经历", section_signal(resume_text, ["实习", "工作经历", "实践经历"]), count_project_signals(resume_text, internship=True), "是否体现真实业务经历"),
        score_dimension("学历背景", section_signal(resume_text, ["教育背景", "学历", "毕业", "本科", "硕士", "博士"]), count_education_signals(resume_text), "教育信息是否完整"),
        score_dimension("科研经历", section_signal(resume_text, ["科研", "论文", "专利", "课题", "实验室"]), count_research_signals(resume_text), "科研能力是否体现"),
        score_dimension("岗位匹配度", max(len(keywords), 1), len(matched), "简历中的技术栈与目标岗位匹配程度"),
        score_dimension("表达质量", max(len(resume_text) // 600, 1), count_bullet_signals(resume_text), "是否有结构化、结果导向表达"),
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
    target_stack = record["target_stack"] or "目标技术栈"
    return normalize_rewrite(
        {
            "headline": f"面向 {role} 的简历改写建议",
            "summaryRewrite": f"聚焦 {role}，突出 {target_stack}，把项目描述改成结果导向表达，优先展示最贴近岗位的经历。",
            "skillsRewrite": [
                f"把技能栏按“核心匹配 / 工程能力 / 了解方向”重组，优先写 {', '.join(matched[:6]) or target_stack}。",
                "避免平铺罗列工具名，改成按岗位价值排序的技术能力表达。",
            ],
            "projectRewrite": build_rewritten_bullets(role, matched),
            "experienceRewrite": [
                "如果有实习经历，补齐业务场景、协作对象、上线结果和个人贡献边界。",
                "如果没有正式实习，可把课程项目、竞赛项目按真实项目方式重写。",
            ],
            "educationRewrite": [
                "教育背景补齐学校、专业、时间；如果成绩、排名、竞赛有优势可以前置。",
                "与岗位相关的课程、科研、比赛可以合并成“补充亮点”。",
            ],
            "missingKeywordsAdvice": missing[:10],
        }
    )


def fallback_interview_pack(record):
    role = record["target_role"]
    matched = record["review"]["jobMatch"].get("matchedKeywords", [])
    missing = record["review"]["jobMatch"].get("missingKeywords", [])
    top_keyword = matched[0] if matched else (missing[0] if missing else "项目")
    questions = [
        {
            "question": f"请你围绕简历里最相关的一个项目，介绍你是如何支撑 {role} 目标能力的？",
            "intent": "考察项目真实性、个人贡献边界和表达能力",
            "answerTips": ["按背景、目标、方案、难点、结果来讲", "明确你本人负责的部分", "最好给出量化结果"],
        },
        {
            "question": f"你在简历中提到了 {top_keyword}，能具体讲讲你在项目中是怎么用它的吗？",
            "intent": "考察技术栈是否真正用过，而不是只写在技能栏",
            "answerTips": ["说清楚使用场景", "说明为什么选它", "补充踩坑和优化点"],
        },
        {
            "question": "如果让你重新做这个项目，你会优先重构哪一块，为什么？",
            "intent": "考察复盘能力和工程判断",
            "answerTips": ["从性能、稳定性、扩展性或可维护性切入", "不要只说表面问题"],
        },
        {
            "question": "简历里哪些经历最能证明你和目标岗位匹配？",
            "intent": "考察岗位理解和自我包装能力",
            "answerTips": ["把经历和岗位 JD 一一对应", "优先说能产生业务价值的部分"],
        },
    ]
    if missing:
        questions.append(
            {
                "question": f"岗位比较看重 {missing[0]}，如果你现在经验不多，你会怎么补足并向面试官解释？",
                "intent": "考察学习能力和风险应对",
                "answerTips": ["承认短板", "给出补足计划", "强调可迁移能力"],
            }
        )
    return normalize_interview_pack(
        {
            "headline": "基于简历的模拟面试题",
            "questions": questions,
        }
    )


def split_keywords(*texts):
    tokens = []
    for text in texts:
        if not text:
            continue
        for piece in re.split(r"[,\n，、/；;|()\[\]：:\s]+", text):
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
    return has_keywords(text, ["论文", "专利", "实验室", "课题", "科研", "竞赛", "发表"])


def count_bullet_signals(text):
    return text.count("•") + text.count("-") + text.count("1.") + text.count("2.") + text.count("3.")


def score_dimension(name, total_signal, positive_signal, reasoning_label):
    if total_signal <= 0:
        score = 35
        verdict = "信息不足"
        reasoning = f"简历里对{name}的呈现较弱，{reasoning_label}没有展开。"
    else:
        ratio = positive_signal / max(total_signal, 1)
        score = clamp_score(int(45 + ratio * 45 + min(positive_signal, 5) * 3))
        if score >= 80:
            verdict = "表现较强"
        elif score >= 65:
            verdict = "中上水平"
        elif score >= 50:
            verdict = "基础可用"
        else:
            verdict = "需要补强"
        reasoning = f"{name}维度目前识别到 {positive_signal} 个有效信号，{reasoning_label}还有提升空间。"
    return {"name": name, "score": score, "verdict": verdict, "reasoning": reasoning}


def clamp_score(value):
    return max(0, min(100, int(value)))


def build_summary(overall, target_role, matched, missing):
    if overall >= 80:
        prefix = "这份简历整体竞争力较强"
    elif overall >= 65:
        prefix = "这份简历具备一定竞争力"
    else:
        prefix = "这份简历目前还需要明显补强"
    matched_text = "、".join(matched[:5]) if matched else "暂无明显匹配技术栈"
    missing_text = "、".join(missing[:5]) if missing else "暂无明显缺口"
    return f"{prefix}，适配目标岗位“{target_role}”。已匹配：{matched_text}。待补充：{missing_text}。"


def build_match_reasoning(matched, missing, target_jd):
    if matched and not missing:
        return "简历中已有较多与目标岗位直接相关的技术关键词，岗位匹配度较高。"
    if matched:
        return f"简历已体现 {len(matched)} 个目标关键词，但仍缺少 {len(missing)} 个岗位关注点，建议围绕 JD 补强。"
    if target_jd:
        return "目标 JD 已提供，但简历中没有明显对应的关键词，建议按岗位要求重写项目与技能部分。"
    return "目前缺少足够的岗位匹配信号，建议补充与目标岗位强相关的技术栈和项目成果。"


def build_highlights(resume_text, matched):
    highlights = []
    if matched:
        highlights.append(f"简历里已经覆盖了部分目标关键词：{'、'.join(matched[:6])}。")
    if section_signal(resume_text, ["项目", "项目经历", "项目经验"]):
        highlights.append("具备项目经历描述基础，可以继续往“背景-动作-结果”方向强化。")
    if section_signal(resume_text, ["实习", "工作经历"]):
        highlights.append("存在实习或工作经历信号，比纯校园简历更容易建立业务可信度。")
    if section_signal(resume_text, ["本科", "硕士", "博士", "大学"]):
        highlights.append("教育背景有体现，基础信息框架较完整。")
    return highlights or ["简历基础结构已具备，适合继续精修为岗位定制版本。"]


def build_risks(resume_text, missing):
    risks = []
    if missing:
        risks.append(f"目标岗位关注的关键词仍有缺失：{'、'.join(missing[:6])}。")
    if not section_signal(resume_text, ["量化", "%", "提升", "降低", "增长", "优化"]):
        risks.append("项目描述偏过程陈述，缺少量化结果或业务影响。")
    if not section_signal(resume_text, ["实习", "工作经历"]):
        risks.append("缺少实习/工作场景支撑，面试官可能会担心真实业务经验不足。")
    if not section_signal(resume_text, ["科研", "论文", "专利", "课题"]):
        risks.append("科研经历未体现，如果目标岗位偏算法/研究，会拉低印象分。")
    return risks[:6]


def build_suggestions(resume_text, missing):
    suggestions = [
        "把技术栈从简单罗列改成“熟练 / 掌握 / 了解”三级表达，避免堆词。",
        "每个项目至少补齐业务场景、技术方案、个人职责、结果指标四部分。",
        "优先把最贴近目标岗位的项目放在最前面，并把关键词写进项目描述而不只是技能栏。",
        "如果有性能优化、稳定性治理、成本优化、效率提升，尽量写出具体数字。",
        "把实习/项目中的协作对象、产出形态、上线结果补出来，增强真实性。",
    ]
    if missing:
        suggestions.append(f"围绕目标岗位补充这些能力的项目表达：{'、'.join(missing[:8])}。")
    if not section_signal(resume_text, ["科研", "论文", "课题"]):
        suggestions.append("如果有课程设计、比赛、实验室经历，也可以作为科研/探索能力的替代补充。")
    return suggestions[:10]


def build_rewritten_bullets(target_role, matched):
    matched_text = "、".join(matched[:4]) if matched else "目标技术栈"
    return [
        f"围绕 {matched_text} 设计并落地核心模块，负责方案拆解、技术实现与联调上线，支撑 {target_role} 相关业务需求快速交付。",
        "针对系统瓶颈完成性能优化与稳定性治理，结合监控和压测定位问题，显著提升页面 / 接口响应效率与可用性。",
        "主导项目关键功能的技术方案选型与实现，推动工程规范、代码质量和协作效率提升，缩短版本交付周期。",
        "结合真实业务场景沉淀可复用能力，将一次性需求抽象为通用组件 / 服务，降低后续维护成本。",
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
    return {
        "headline": str(payload.get("headline", "基于简历的模拟面试题")),
        "questions": questions[:12],
    }


def main():
    server = ThreadingHTTPServer((HOST, PORT), ResumeReviewHandler)
    print(f"Resume review server running at http://{HOST}:{PORT}/web_mvp/")
    print(f"API health: http://{HOST}:{PORT}/api/health")
    server.serve_forever()


if __name__ == "__main__":
    main()
