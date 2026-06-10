import argparse
import json
import os
import re
import time
from collections import defaultdict
from html import unescape
from typing import Dict, List, Tuple
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen

from bs4 import BeautifulSoup


USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/126.0.0.0 Safari/537.36"
)


CATEGORY_RULES: List[Tuple[str, List[str]]] = [
    ("java_base", ["java基础", "java 基础", "java面向对象", "java语法", "数据类型", "异常"]),
    ("java_collection", ["集合", "collection", "list", "set", "map"]),
    ("jvm", ["jvm", "垃圾回收", "gc", "类加载", "内存模型"]),
    ("concurrency", ["并发", "多线程", "线程", "锁", "volatile", "synchronized", "aqs"]),
    ("spring", ["spring", "springboot", "spring boot", "springmvc", "aop", "ioc"]),
    ("mysql", ["mysql", "sql", "索引", "事务", "数据库"]),
    ("redis", ["redis", "缓存"]),
    ("mq", ["mq", "消息队列", "kafka", "rabbitmq", "rocketmq"]),
    ("network", ["网络", "http", "tcp", "udp", "socket"]),
    ("os", ["操作系统", "linux", "进程", "线程调度", "内存管理"]),
    ("design_pattern", ["设计模式", "工厂模式", "单例", "策略模式", "观察者"]),
    ("microservice", ["微服务", "分布式", "注册中心", "熔断", "限流", "网关"]),
    ("algorithm", ["算法", "数据结构", "链表", "二叉树", "排序", "动态规划"]),
    ("interview_misc", ["项目", "场景", "面试技巧", "hr", "综合"]),
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="读取目录 JSON，批量抓详情页正文并按技术板块归组保存。")
    parser.add_argument("--input", help="目录 JSON 文件路径")
    parser.add_argument(
        "--output-dir",
        default="question_bank/backend/raw_pages",
        help="输出目录，默认按板块写入多个 JSON 文件",
    )
    parser.add_argument("--limit", type=int, default=0, help="只抓前 N 条，0 表示全部")
    parser.add_argument("--delay", type=float, default=0.8, help="每次请求间隔秒数")
    parser.add_argument(
        "--same-domain-only",
        action="store_true",
        help="只抓与目录页同域名的详情链接",
    )
    parser.add_argument(
        "--clean-existing-dir",
        help="清洗已抓取好的目录，读取其中各分组 JSON 并输出到新的目录，无需重新联网抓取",
    )
    return parser.parse_args()


def fetch_html(url: str) -> str:
    request = Request(
        url,
        headers={
            "User-Agent": USER_AGENT,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        },
    )
    with urlopen(request, timeout=30) as response:
        raw = response.read()
        charset = response.headers.get_content_charset() or "utf-8"
        try:
            return raw.decode(charset, errors="replace")
        except LookupError:
            return raw.decode("utf-8", errors="replace")


def clean_text(text: str) -> str:
    text = unescape(text or "")
    text = text.replace("\r", "\n").replace("\u00a0", " ")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def extract_article_node(soup: BeautifulSoup):
    selectors = [
        "article",
        ".post-content",
        ".article-content",
        ".entry-content",
        ".single-content",
        "#content",
        "main",
        "body",
    ]
    for selector in selectors:
        node = soup.select_one(selector)
        if node:
            return node
    return soup


def remove_noise_nodes(node) -> None:
    selectors = [
        "script",
        "style",
        "nav",
        "aside",
        "footer",
        "form",
        ".sidebar",
        ".related-posts",
        ".recommend",
        ".adsbygoogle",
        ".advertisement",
        ".post-tags",
        ".breadcrumbs",
        ".toc",
        ".catalog",
        ".directory",
        ".share",
        ".author-box",
    ]
    for selector in selectors:
        for item in node.select(selector):
            item.decompose()


def strip_noise_lines(lines: List[str]) -> List[str]:
    noise_keywords = [
        "一则或许对你有用的小广告",
        "加入小哈的星球",
        "查看介绍",
        "点击围观",
        "1v1 提问",
        "简历修改",
        "学习打卡",
        "每月赠书",
        "Spring AI 项目实战",
        "从零手撸",
        "演示链接",
        "上一题",
        "下一题",
        "上一篇",
        "下一篇",
        "http://",
        "https://",
        "新开坑项目",
        "正在更新中",
        "截止目前",
        "累计输出",
        "小伙伴加入学习",
        "演示链接",
        "已完结，基于",
    ]
    cleaned: List[str] = []
    for line in lines:
        line = clean_text(line)
        if not line:
            continue
        if re.fullmatch(r"[，。、“”‘’：:；;（）()【】\[\]…\-—,.!?？!]+", line):
            continue
        if any(keyword in line for keyword in noise_keywords):
            continue
        cleaned.append(line)
    return cleaned


def crop_meaningful_content(lines: List[str], question_title: str) -> List[str]:
    if not lines:
        return []

    start_index = 0
    for idx, line in enumerate(lines):
        if question_title and question_title in line:
            start_index = idx
            break
        if line in {"面试考察点", "核心答案", "深度解析"}:
            start_index = max(0, idx - 1)
            break

    end_markers = {"上一题", "下一题", "上一篇", "下一篇"}
    end_index = len(lines)
    for idx in range(start_index, len(lines)):
        if lines[idx] in end_markers:
            end_index = idx
            break

    return lines[start_index:end_index]


def remove_promo_block(lines: List[str]) -> List[str]:
    promo_start = None
    promo_end = None

    for idx, line in enumerate(lines):
        if "欢迎" == line or "欢迎" in line:
            promo_start = idx
            break

    if promo_start is None:
        return lines

    for idx in range(promo_start + 1, len(lines)):
        if lines[idx] in {"面试考察点", "核心答案", "深度解析"}:
            promo_end = idx
            break

    if promo_end is None:
        return lines

    return lines[:promo_start] + lines[promo_end:]


def html_to_text(html: str) -> str:
    html = re.sub(r"(?is)<script.*?>.*?</script>", " ", html)
    html = re.sub(r"(?is)<style.*?>.*?</style>", " ", html)
    soup = BeautifulSoup(html, "html.parser")
    node = extract_article_node(soup)
    remove_noise_nodes(node)
    text = node.get_text("\n", strip=True)
    return clean_text(text)


def load_directory_items(path: str) -> Dict:
    with open(path, "r", encoding="utf-8") as file:
        return json.load(file)


def infer_bucket(section_title: str, question_title: str, url: str) -> str:
    haystack = f"{section_title} {question_title} {url}".lower()
    for bucket, keywords in CATEGORY_RULES:
        for keyword in keywords:
            if keyword.lower() in haystack:
                return bucket
    return "uncategorized"


def sanitize_filename(name: str) -> str:
    name = re.sub(r"[<>:\"/\\\\|?*]+", "_", name)
    name = re.sub(r"\s+", "_", name).strip("._ ")
    return name or "untitled"


def should_keep_url(source_url: str, detail_url: str, same_domain_only: bool) -> bool:
    if not same_domain_only:
        return True
    return urlparse(source_url).netloc == urlparse(detail_url).netloc


def collect_items(payload: Dict, limit: int, same_domain_only: bool) -> List[Dict]:
    source_url = payload.get("source_url", "")
    items = payload.get("items", [])
    if not isinstance(items, list):
        return []

    filtered = []
    for item in items:
        if not isinstance(item, dict):
            continue
        url = item.get("url", "")
        if not url or not should_keep_url(source_url, url, same_domain_only):
            continue
        filtered.append(item)

    if limit > 0:
        return filtered[:limit]
    return filtered


def extract_page_title(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")
    if soup.title:
        return clean_text(soup.title.get_text(" ", strip=True))
    return ""


def clean_detail_content(content_text: str, question_title: str, page_title: str) -> str:
    lines = [clean_text(line) for line in content_text.splitlines()]
    lines = [line for line in lines if line]

    filtered_lines: List[str] = []
    seen = set()
    for line in lines:
        if line in {question_title, page_title} and line in seen:
            continue
        filtered_lines.append(line)
        seen.add(line)

    filtered_lines = strip_noise_lines(filtered_lines)
    filtered_lines = crop_meaningful_content(filtered_lines, question_title)
    filtered_lines = remove_promo_block(filtered_lines)
    filtered_lines = strip_noise_lines(filtered_lines)

    deduped: List[str] = []
    last_line = None
    for line in filtered_lines:
        if line == last_line:
            continue
        deduped.append(line)
        last_line = line

    return "\n".join(deduped).strip()


def crawl_detail_items(items: List[Dict], delay: float) -> Tuple[Dict[str, List[Dict]], List[Dict]]:
    grouped: Dict[str, List[Dict]] = defaultdict(list)
    failures: List[Dict] = []

    total = len(items)
    for index, item in enumerate(items, start=1):
        section_title = clean_text(item.get("section_title", ""))
        question_title = clean_text(item.get("title", ""))
        detail_url = item.get("url", "")
        bucket = infer_bucket(section_title, question_title, detail_url)

        try:
            html = fetch_html(detail_url)
            page_title = extract_page_title(html)
            content_text = html_to_text(html)
            content_text = clean_detail_content(content_text, question_title, page_title)

            grouped[bucket].append(
                {
                    "section_title": section_title,
                    "question_title": question_title,
                    "bucket": bucket,
                    "url": detail_url,
                    "page_title": page_title,
                    "content_text": content_text,
                }
            )
            print(f"[{index}/{total}] ok  {bucket}  {question_title}")
        except (HTTPError, URLError, TimeoutError, ValueError) as exc:
            failures.append(
                {
                    "section_title": section_title,
                    "question_title": question_title,
                    "url": detail_url,
                    "error": str(exc),
                }
            )
            print(f"[{index}/{total}] fail  {question_title}  {exc}")

        if delay > 0 and index < total:
            time.sleep(delay)

    return grouped, failures


def write_grouped_files(output_dir: str, grouped: Dict[str, List[Dict]], failures: List[Dict], source_url: str) -> None:
    os.makedirs(output_dir, exist_ok=True)

    manifest = {
        "source_url": source_url,
        "group_count": len(grouped),
        "groups": [],
        "failure_count": len(failures),
        "failures_file": "failures.json",
    }

    for bucket, records in sorted(grouped.items()):
        filename = sanitize_filename(bucket) + ".json"
        filepath = os.path.join(output_dir, filename)
        payload = {
            "bucket": bucket,
            "count": len(records),
            "items": records,
        }
        with open(filepath, "w", encoding="utf-8") as file:
            json.dump(payload, file, ensure_ascii=False, indent=2)
        manifest["groups"].append(
            {
                "bucket": bucket,
                "count": len(records),
                "file": filename,
            }
        )

    with open(os.path.join(output_dir, "manifest.json"), "w", encoding="utf-8") as file:
        json.dump(manifest, file, ensure_ascii=False, indent=2)

    with open(os.path.join(output_dir, "failures.json"), "w", encoding="utf-8") as file:
        json.dump({"count": len(failures), "items": failures}, file, ensure_ascii=False, indent=2)


def clean_existing_group_dir(input_dir: str, output_dir: str) -> Dict[str, int]:
    os.makedirs(output_dir, exist_ok=True)

    success_groups = 0
    total_items = 0
    source_url = ""

    for filename in os.listdir(input_dir):
        if not filename.endswith(".json"):
            continue
        if filename in {"manifest.json", "failures.json"}:
            continue

        input_path = os.path.join(input_dir, filename)
        with open(input_path, "r", encoding="utf-8") as file:
            payload = json.load(file)

        bucket = payload.get("bucket", os.path.splitext(filename)[0])
        items = payload.get("items", [])
        cleaned_items = []

        for item in items:
            question_title = clean_text(item.get("question_title", ""))
            page_title = clean_text(item.get("page_title", ""))
            content_text = clean_text(item.get("content_text", ""))
            cleaned_text = clean_detail_content(content_text, question_title, page_title)

            cleaned_item = dict(item)
            cleaned_item["content_text"] = cleaned_text
            cleaned_items.append(cleaned_item)
            total_items += 1

        output_path = os.path.join(output_dir, filename)
        with open(output_path, "w", encoding="utf-8") as file:
            json.dump(
                {
                    "bucket": bucket,
                    "count": len(cleaned_items),
                    "items": cleaned_items,
                },
                file,
                ensure_ascii=False,
                indent=2,
            )
        success_groups += 1

    manifest_path = os.path.join(input_dir, "manifest.json")
    if os.path.exists(manifest_path):
        with open(manifest_path, "r", encoding="utf-8") as file:
            manifest = json.load(file)
        source_url = manifest.get("source_url", "")
        with open(os.path.join(output_dir, "manifest.json"), "w", encoding="utf-8") as file:
            json.dump(manifest, file, ensure_ascii=False, indent=2)

    failures_path = os.path.join(input_dir, "failures.json")
    if os.path.exists(failures_path):
        with open(failures_path, "r", encoding="utf-8") as src, open(
            os.path.join(output_dir, "failures.json"), "w", encoding="utf-8"
        ) as dst:
            dst.write(src.read())

    return {
        "group_count": success_groups,
        "item_count": total_items,
        "source_url": source_url,
    }


def main() -> int:
    args = parse_args()

    if args.clean_existing_dir:
        summary = clean_existing_group_dir(args.clean_existing_dir, args.output_dir)
        print(
            json.dumps(
                {
                    "ok": True,
                    "mode": "clean_existing_dir",
                    "group_count": summary["group_count"],
                    "item_count": summary["item_count"],
                    "output_dir": os.path.abspath(args.output_dir),
                },
                ensure_ascii=False,
            )
        )
        return 0

    if not args.input:
        raise SystemExit("Error: --input is required unless using --clean-existing-dir")

    payload = load_directory_items(args.input)
    items = collect_items(payload, args.limit, args.same_domain_only)
    grouped, failures = crawl_detail_items(items, args.delay)
    write_grouped_files(args.output_dir, grouped, failures, payload.get("source_url", ""))

    summary = {
        "ok": True,
        "input_count": len(items),
        "success_count": sum(len(records) for records in grouped.values()),
        "failure_count": len(failures),
        "group_count": len(grouped),
        "output_dir": os.path.abspath(args.output_dir),
    }
    print(json.dumps(summary, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
