import argparse
import json
import os
import re
import sys
import unicodedata
from html import unescape
from typing import Any, Dict, List, Optional, Tuple
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen

try:
    from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
    from playwright.sync_api import sync_playwright
except ImportError:
    PlaywrightTimeoutError = Exception
    sync_playwright = None


DEFAULT_MODEL = "deepseek-v4-flash"
DEFAULT_BASE_URL = "https://api.deepseek.com/chat/completions"
DEFAULT_OUTPUT = "frontend_questions.json"
FETCH_MODE_CHOICES = ["auto", "http", "browser"]
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/126.0.0.0 Safari/537.36"
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Fetch a public article, ask an LLM to extract interview questions, and save JSON."
    )
    source_group = parser.add_mutually_exclusive_group(required=True)
    source_group.add_argument("--url", help="Public article URL to fetch.")
    source_group.add_argument("--input-file", help="Local UTF-8 text file containing article text.")
    source_group.add_argument("--clean-json", help="Clean an existing extracted JSON file without calling the model.")

    parser.add_argument("--title", help="Optional source title. Auto-derived when omitted.")
    parser.add_argument("--output", default=DEFAULT_OUTPUT, help="Output JSON file path.")
    parser.add_argument("--raw-output", help="Optional file path to save the raw model response.")
    parser.add_argument("--model", default=DEFAULT_MODEL, help="Model name.")
    parser.add_argument(
        "--fetch-mode",
        default="auto",
        choices=FETCH_MODE_CHOICES,
        help="How to fetch article content: auto, http, or browser.",
    )
    parser.add_argument(
        "--base-url",
        default=DEFAULT_BASE_URL,
        help="OpenAI-compatible chat completions endpoint.",
    )
    parser.add_argument(
        "--api-key",
        default=os.getenv("DEEPSEEK_API_KEY", ""),
        help="API key. Defaults to DEEPSEEK_API_KEY.",
    )
    parser.add_argument(
        "--max-chars",
        type=int,
        default=50000,
        help="Maximum article characters sent to the model.",
    )
    parser.add_argument(
        "--temperature",
        type=float,
        default=0.1,
        help="Sampling temperature.",
    )
    return parser.parse_args()


def detect_html_charset(raw_bytes: bytes, header_charset: Optional[str]) -> str:
    if header_charset:
        return header_charset

    head = raw_bytes[:4096].decode("ascii", errors="ignore")
    patterns = [
        r'<meta[^>]+charset=["\']?([\w-]+)',
        r'<meta[^>]+content=["\'][^"\']*charset=([\w-]+)',
    ]
    for pattern in patterns:
        match = re.search(pattern, head, flags=re.IGNORECASE)
        if match:
            return match.group(1).lower()

    return "utf-8"


def looks_garbled(text: str) -> bool:
    markers = ["锛", "銆", "鈥", "鍓", "闈", ""]
    return sum(text.count(marker) for marker in markers) >= 3


def fetch_url(url: str) -> str:
    request = Request(
        url,
        headers={
            "User-Agent": USER_AGENT,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        },
    )
    with urlopen(request, timeout=30) as response:
        raw_bytes = response.read()
        header_charset = response.headers.get_content_charset()
        charset = detect_html_charset(raw_bytes, header_charset)

        candidates = []
        for candidate in [charset, "utf-8", "gb18030", "gbk"]:
            if candidate and candidate not in candidates:
                candidates.append(candidate)

        decoded_versions = []
        for candidate in candidates:
            try:
                decoded_versions.append(raw_bytes.decode(candidate, errors="replace"))
            except LookupError:
                continue

        for decoded in decoded_versions:
            if not looks_garbled(decoded):
                return decoded

        return decoded_versions[0] if decoded_versions else raw_bytes.decode("utf-8", errors="replace")


def fetch_url_with_browser(url: str) -> str:
    if sync_playwright is None:
        raise RuntimeError(
            "Playwright is not installed. Install it and run `playwright install chromium` first."
        )

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        page = browser.new_page(user_agent=USER_AGENT, locale="zh-CN")
        try:
            page.goto(url, wait_until="domcontentloaded", timeout=45000)
            page.wait_for_timeout(3000)
            for selector in [
                "article",
                "#article-root",
                ".article-content",
                ".article",
                "#content_views",
                "#cnblogs_post_body",
                "main",
                "body",
            ]:
                locator = page.locator(selector).first
                if locator.count() > 0:
                    try:
                        locator.wait_for(timeout=5000)
                        break
                    except PlaywrightTimeoutError:
                        continue
            return page.content()
        finally:
            browser.close()


def read_input_file(path: str) -> str:
    with open(path, "r", encoding="utf-8") as file:
        return file.read()


def html_to_text(html: str) -> str:
    html = re.sub(r"(?is)<script.*?>.*?</script>", " ", html)
    html = re.sub(r"(?is)<style.*?>.*?</style>", " ", html)
    html = re.sub(r"(?is)<noscript.*?>.*?</noscript>", " ", html)

    blocks = [
        r"(?is)<article.*?>(.*?)</article>",
        r'(?is)<div[^>]+id=["\']cnblogs_post_body["\'][^>]*>(.*?)</div>',
        r'(?is)<div[^>]+class=["\'][^"\']*postBody[^"\']*["\'][^>]*>(.*?)</div>',
        r'(?is)<main.*?>(.*?)</main>',
        r"(?is)<body.*?>(.*?)</body>",
    ]

    content = html
    for pattern in blocks:
        match = re.search(pattern, html)
        if match:
            content = match.group(1)
            break

    content = re.sub(r"(?i)<br\s*/?>", "\n", content)
    content = re.sub(r"(?i)</p>", "\n", content)
    content = re.sub(r"(?i)</div>", "\n", content)
    content = re.sub(r"(?i)</li>", "\n", content)
    content = re.sub(r"(?i)</h[1-6]>", "\n", content)
    content = re.sub(r"(?i)<li[^>]*>", "- ", content)
    content = re.sub(r"(?is)<[^>]+>", " ", content)

    text = unescape(content)
    text = text.replace("\r", "\n").replace("\u00a0", " ")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def should_retry_with_browser(exc: Exception, html: str = "") -> bool:
    if isinstance(exc, HTTPError) and exc.code in {403, 412, 418, 429, 451, 521, 522, 523}:
        return True

    lowered = html.lower()
    markers = [
        "please wait",
        "captcha",
        "验证",
        "访问过于频繁",
        "安全验证",
        "检测中",
    ]
    return any(marker in lowered for marker in markers)


def derive_title(raw_text: str, supplied_title: Optional[str], url: Optional[str]) -> str:
    if supplied_title:
        return supplied_title

    lines = [line.strip() for line in raw_text.splitlines() if line.strip()]
    for line in lines[:10]:
        if 4 <= len(line) <= 120:
            return line

    if url:
        return urlparse(url).netloc
    return "Untitled Source"


def truncate_text(text: str, max_chars: int) -> str:
    if len(text) <= max_chars:
        return text
    return text[:max_chars] + "\n\n[TRUNCATED]"


def build_prompt(title: str, article_text: str) -> str:
    return f"""你现在是一个“技术面试题库抽取器”，任务是从给定的前端八股文、技术文章或学习笔记中，提取出适合进入面试题库的题目。

目标：
1. 从文章中识别出所有明确或隐含的前端面试题
2. 将题目标准化为自然、清晰、适合面试场景的问法
3. 提取每道题对应的简要答案要点
4. 给题目打上分类、标签、难度
5. 尽量穷举文章中的可提问题目，而不是只做摘要
6. 严格输出 JSON，不要输出任何解释性文字

抽取规则：
1. 只提取“能作为面试题”的内容
2. 不要提取目录、标题口号、广告语、无信息量句子
3. 目标是高召回抽取：宁可多提取、后续去重，也不要遗漏明显可提问的知识点
4. 不要为了简洁把多个知识点合并成一道大题；如果一个段落中出现多个可独立提问的知识点，应拆成多道题
5. 只有在多个点天然必须一起回答时，才允许合并成一道综合题
6. 题目要改写成标准问法
7. 如果原文答案很长，只提炼 3 到 6 条答案要点
8. 如果某段内容适合作为追问，也要抽出来
9. 不要编造原文没有提到的知识点
10. source_type 固定输出为 "baguwen"
11. domain 固定输出为 "frontend"

高召回要求：
1. 每个一级标题、二级标题、列表项、知识点总结处，都要检查是否能拆出独立面试题
2. 如果文章覆盖面很广，questions 数量通常应不少于 20 道；只有当原文确实很短时，才允许少于 20 道
3. 优先输出细粒度题目，其次再输出综合题
4. 对于以下常见情况，要倾向拆题而不是合题：
   - “概念 + 原理”
   - “对比 + 使用场景”
   - “优缺点 + 底层实现”
   - “流程 + 优化”
5. 如果原文中出现“必考、常问、重点、核心、原理、区别、流程、实现、优化、场景”等词，优先视为独立题目线索
6. 如果某个知识块中同时包含“是什么、为什么、怎么做、有什么问题”，至少拆成 2 到 4 道题

分类范围：
- javascript
- es6
- browser
- network
- css
- framework
- engineering
- performance
- security
- scenario
- handwrite
- other

难度范围：
- junior
- mid
- senior

题型范围：
- concept
- principle
- comparison
- scenario
- project
- optimization
- handwrite

输出 JSON 结构如下：
{{
  "source_title": "string",
  "source_type": "baguwen",
  "domain": "frontend",
  "questions": [
    {{
      "question": "标准化后的题目",
      "question_type": "concept | principle | comparison | scenario | project | optimization | handwrite",
      "category": "javascript | es6 | browser | network | css | framework | engineering | performance | security | scenario | handwrite | other",
      "difficulty": "junior | mid | senior",
      "tags": ["标签1", "标签2"],
      "answer_points": [
        "答案要点1",
        "答案要点2"
      ],
      "follow_ups": [
        "可能的追问1",
        "可能的追问2"
      ],
      "source_excerpt": "对应原文中的关键片段，尽量简短"
    }}
  ]
}}

最终输出要求：
- 只返回一个合法 JSON 对象
- 不要添加任何说明文字
- 不要添加 markdown 代码块
- 如果某个字段缺失，使用空数组或空字符串，不要省略字段
- questions 请尽量完整覆盖文章中的可提问知识点，不要只挑最显眼的 5 到 10 道题

下面是要抽取的文章内容：

标题：{title}

正文：
{article_text}
"""


def call_model(
    api_key: str,
    base_url: str,
    model: str,
    prompt: str,
    temperature: float,
) -> str:
    if not api_key:
        raise ValueError("Missing API key. Set DEEPSEEK_API_KEY or pass --api-key.")

    payload = {
        "model": model,
        "temperature": temperature,
        "messages": [
            {
                "role": "system",
                "content": (
                    "You extract structured interview questions and must return only valid JSON."
                ),
            },
            {"role": "user", "content": prompt},
        ],
        "response_format": {"type": "json_object"},
    }

    request = Request(
        base_url,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )

    with urlopen(request, timeout=120) as response:
        body = response.read().decode("utf-8", errors="replace")
        data = json.loads(body)
        return data["choices"][0]["message"]["content"]


def repair_json_with_model(
    api_key: str,
    base_url: str,
    model: str,
    broken_json_text: str,
) -> Dict[str, Any]:
    repair_prompt = f"""You are a JSON repair tool.
The following text is intended to be a JSON object but may contain minor formatting issues.
Repair it into valid JSON only.
Return only one valid JSON object and do not add commentary.

Broken JSON:
{broken_json_text}
"""
    repaired = call_model(
        api_key=api_key,
        base_url=base_url,
        model=model,
        prompt=repair_prompt,
        temperature=0,
    )
    return parse_model_json(repaired)


def strip_code_fences(text: str) -> str:
    stripped = text.strip()
    if stripped.startswith("```"):
        stripped = re.sub(r"^```(?:json)?\s*", "", stripped)
        stripped = re.sub(r"\s*```$", "", stripped)
    return stripped.strip()


def count_unescaped_quotes(text: str) -> int:
    count = 0
    escaped = False
    for char in text:
        if char == "\\" and not escaped:
            escaped = True
            continue
        if char == '"' and not escaped:
            count += 1
        escaped = False
    return count


def fix_odd_quote_line(line: str) -> str:
    if count_unescaped_quotes(line) % 2 == 0:
        return line

    if re.search(r',\s*$', line):
        return re.sub(r',\s*$', '",', line)
    if re.search(r'\]\s*$', line):
        return re.sub(r'\]\s*$', '"]', line)
    if re.search(r'}\s*$', line):
        return re.sub(r'}\s*$', '"}', line)
    return line + '"'


def sanitize_broken_json_text(text: str) -> str:
    lines = text.splitlines()
    fixed_lines = [fix_odd_quote_line(line) for line in lines]
    fixed = "\n".join(fixed_lines)
    fixed = re.sub(r",(\s*[}\]])", r"\1", fixed)
    return fixed


def recover_partial_payload(raw_text: str, title: str) -> Dict[str, Any]:
    stripped = sanitize_broken_json_text(strip_code_fences(raw_text))
    source_title_match = re.search(r'"source_title"\s*:\s*"([^"]*)"', stripped)
    source_title = source_title_match.group(1) if source_title_match else title
    domain_match = re.search(r'"domain"\s*:\s*"([^"]*)"', stripped)
    domain = domain_match.group(1) if domain_match else "frontend"
    source_type_match = re.search(r'"source_type"\s*:\s*"([^"]*)"', stripped)
    source_type = source_type_match.group(1) if source_type_match else "baguwen"

    questions_start = stripped.find('"questions"')
    if questions_start == -1:
        return {
            "source_title": source_title,
            "source_type": source_type,
            "domain": domain,
            "questions": [],
        }

    array_start = stripped.find("[", questions_start)
    if array_start == -1:
        return {
            "source_title": source_title,
            "source_type": source_type,
            "domain": domain,
            "questions": [],
        }

    objects = []
    depth = 0
    in_string = False
    escaped = False
    current = []

    for char in stripped[array_start + 1 :]:
        current.append(char)
        if escaped:
            escaped = False
            continue
        if char == "\\":
            escaped = True
            continue
        if char == '"':
            in_string = not in_string
            continue
        if in_string:
            continue
        if char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                snippet = "".join(current).strip()
                start = snippet.find("{")
                end = snippet.rfind("}")
                if start != -1 and end != -1 and end > start:
                    objects.append(snippet[start : end + 1])
                current = []
        elif char == "]" and depth == 0:
            break

    parsed_questions = []
    for snippet in objects:
        try:
            candidate = sanitize_broken_json_text(snippet)
            parsed = json.loads(candidate)
            if isinstance(parsed, dict):
                parsed_questions.append(parsed)
        except json.JSONDecodeError:
            continue

    return {
        "source_title": source_title,
        "source_type": source_type,
        "domain": domain,
        "questions": parsed_questions,
    }


def parse_model_json(raw_text: str) -> Dict[str, Any]:
    stripped = strip_code_fences(raw_text)
    try:
        return json.loads(stripped)
    except json.JSONDecodeError:
        stripped = sanitize_broken_json_text(stripped)
        start = stripped.find("{")
        end = stripped.rfind("}")
        if start != -1 and end != -1 and end > start:
            candidate = stripped[start : end + 1]
            candidate = sanitize_broken_json_text(candidate)
            return json.loads(candidate)
        raise


def clean_replacement_chars(text: str, field_name: str) -> str:
    if not text:
        return ""

    text = text.replace("\uff1f", "？").replace("\uff01", "！")
    text = text.replace("�", "\ufffd")

    if field_name == "question":
        text = re.sub(r"\ufffd+$", "？", text)
        text = re.sub(r"\ufffd+(?=[它他她这那哪些什么为什么如何是否怎么哪里哪种哪类])", "，", text)
        text = re.sub(r"(?<=[\u4e00-\u9fffA-Za-z0-9])\ufffd(?=[\u4e00-\u9fffA-Za-z0-9])", "，", text)
        text = text.replace("\ufffd", "")
        if text and text[-1] not in "？?！!。":
            text += "？"
        return text

    text = re.sub(r"(?<=[\u4e00-\u9fffA-Za-z0-9])\ufffd(?=\s*[A-Za-z0-9])", "：", text)
    text = re.sub(r"(?<=[\u4e00-\u9fffA-Za-z0-9])\ufffd(?=\s*[\u4e00-\u9fff])", "，", text)
    text = text.replace("\ufffd", "")
    return text


def normalize_spacing_and_punctuation(text: str) -> str:
    if not text:
        return ""

    text = unicodedata.normalize("NFKC", text)
    text = re.sub(r"\s+", " ", text).strip()
    text = re.sub(r"\s*([，。；：！？])\s*", r"\1", text)
    text = re.sub(r"([A-Za-z])，([A-Za-z])", r"\1,\2", text)
    text = re.sub(r"([A-Za-z])：([A-Za-z])", r"\1: \2", text)
    text = re.sub(r"([A-Za-z])？([A-Za-z])", r"\1? \2", text)
    return text.strip()


def clean_text_field(text: str, field_name: str) -> str:
    cleaned = clean_replacement_chars(str(text), field_name)
    cleaned = normalize_spacing_and_punctuation(cleaned)
    return cleaned


def normalize_question(item: Dict[str, Any]) -> Dict[str, Any]:
    def ensure_list(value: Any) -> List[str]:
        if isinstance(value, list):
            return [clean_text_field(str(v).strip(), "list_item") for v in value if str(v).strip()]
        if isinstance(value, str) and value.strip():
            return [clean_text_field(value.strip(), "list_item")]
        return []

    return {
        "question": clean_text_field(str(item.get("question", "")).strip(), "question"),
        "question_type": str(item.get("question_type", "concept")).strip() or "concept",
        "category": str(item.get("category", "other")).strip() or "other",
        "difficulty": str(item.get("difficulty", "junior")).strip() or "junior",
        "tags": ensure_list(item.get("tags", [])),
        "answer_points": ensure_list(item.get("answer_points", [])),
        "follow_ups": ensure_list(item.get("follow_ups", [])),
        "source_excerpt": clean_text_field(str(item.get("source_excerpt", "")).strip(), "excerpt"),
    }


def normalize_payload(payload: Dict[str, Any], title: str) -> Dict[str, Any]:
    questions = payload.get("questions", [])
    if not isinstance(questions, list):
        questions = []

    normalized_questions = []
    for item in questions:
        if not isinstance(item, dict):
            continue
        normalized = normalize_question(item)
        if normalized["question"]:
            normalized_questions.append(normalized)

    return {
        "source_title": clean_text_field(str(payload.get("source_title", title)).strip() or title, "title"),
        "source_type": "baguwen",
        "domain": "frontend",
        "questions": normalized_questions,
    }


def write_json(path: str, data: Dict[str, Any]) -> None:
    with open(path, "w", encoding="utf-8") as file:
        json.dump(data, file, ensure_ascii=False, indent=2)


def write_text(path: str, text: str) -> None:
    with open(path, "w", encoding="utf-8") as file:
        file.write(text)


def load_source(args: argparse.Namespace) -> Tuple[str, str]:
    if args.url:
        if args.fetch_mode == "browser":
            html = fetch_url_with_browser(args.url)
            text = html_to_text(html)
            return html, text

        if args.fetch_mode == "http":
            html = fetch_url(args.url)
            text = html_to_text(html)
            return html, text

        try:
            html = fetch_url(args.url)
            if should_retry_with_browser(Exception(), html):
                browser_html = fetch_url_with_browser(args.url)
                return browser_html, html_to_text(browser_html)
            return html, html_to_text(html)
        except (HTTPError, URLError) as exc:
            if should_retry_with_browser(exc):
                browser_html = fetch_url_with_browser(args.url)
                return browser_html, html_to_text(browser_html)
            raise
    text = read_input_file(args.input_file)
    return text, text


def clean_existing_json(input_path: str, output_path: str) -> Dict[str, Any]:
    with open(input_path, "r", encoding="utf-8") as file:
        payload = json.load(file)

    title = str(payload.get("source_title", "Untitled Source")).strip() or "Untitled Source"
    normalized = normalize_payload(payload, title)
    write_json(output_path, normalized)
    return normalized


def main() -> int:
    args = parse_args()

    try:
        if args.clean_json:
            normalized = clean_existing_json(args.clean_json, args.output)
            print(
                json.dumps(
                    {
                        "ok": True,
                        "source_title": normalized["source_title"],
                        "question_count": len(normalized["questions"]),
                        "output": os.path.abspath(args.output),
                        "mode": "clean_json",
                    },
                    ensure_ascii=False,
                )
            )
            return 0

        _, clean_text = load_source(args)
        title = derive_title(clean_text, args.title, args.url)
        article_text = truncate_text(clean_text, args.max_chars)
        prompt = build_prompt(title, article_text)
        raw_response = call_model(
            api_key=args.api_key,
            base_url=args.base_url,
            model=args.model,
            prompt=prompt,
            temperature=args.temperature,
        )

        if args.raw_output:
            write_text(args.raw_output, raw_response)

        try:
            parsed = parse_model_json(raw_response)
        except json.JSONDecodeError:
            try:
                parsed = repair_json_with_model(
                    api_key=args.api_key,
                    base_url=args.base_url,
                    model=args.model,
                    broken_json_text=raw_response,
                )
            except json.JSONDecodeError:
                parsed = recover_partial_payload(raw_response, title)

        normalized = normalize_payload(parsed, title)
        write_json(args.output, normalized)

        print(
            json.dumps(
                {
                    "ok": True,
                    "source_title": normalized["source_title"],
                    "question_count": len(normalized["questions"]),
                    "output": os.path.abspath(args.output),
                    "raw_output": os.path.abspath(args.raw_output) if args.raw_output else "",
                },
                ensure_ascii=False,
            )
        )
        return 0
    except (HTTPError, URLError) as exc:
        print(f"Network error: {exc}", file=sys.stderr)
        return 1
    except json.JSONDecodeError as exc:
        print(f"Failed to parse model response as JSON: {exc}", file=sys.stderr)
        return 1
    except Exception as exc:  # noqa: BLE001
        print(f"Error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
