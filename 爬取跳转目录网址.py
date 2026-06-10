import argparse
import json
import re
from typing import Dict, List, Optional
from urllib.parse import urljoin, urlparse
from urllib.request import Request, urlopen

from bs4 import BeautifulSoup, Tag


USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/126.0.0.0 Safari/537.36"
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="抓取目录页中的分类、子题标题和跳转链接。"
    )
    parser.add_argument("--url", required=True, help="目录页网址")
    parser.add_argument(
        "--output",
        default="directory_links.json",
        help="输出 JSON 文件路径",
    )
    parser.add_argument(
        "--same-domain-only",
        action="store_true",
        help="只保留与目录页同域名的链接",
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
        return raw.decode(charset, errors="replace")


def clean_text(text: str) -> str:
    text = re.sub(r"\s+", " ", text or "").strip()
    return text


def normalize_url(base_url: str, href: str) -> str:
    return urljoin(base_url, href.strip())


def is_valid_link(url: str, base_url: str, same_domain_only: bool) -> bool:
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"}:
        return False
    if same_domain_only and parsed.netloc != urlparse(base_url).netloc:
        return False
    return True


def extract_sections(soup: BeautifulSoup, base_url: str, same_domain_only: bool) -> List[Dict]:
    content_root = soup.find("main") or soup.find("article") or soup.body or soup
    sections: List[Dict] = []
    current_section: Optional[Dict] = None
    seen_urls = set()

    for node in content_root.descendants:
        if not isinstance(node, Tag):
            continue

        if node.name in {"h1", "h2", "h3"}:
            title = clean_text(node.get_text(" ", strip=True))
            if title:
                current_section = {"section_title": title, "items": []}
                sections.append(current_section)
            continue

        if node.name != "a":
            continue

        href = node.get("href")
        if not href:
            continue

        full_url = normalize_url(base_url, href)
        if not is_valid_link(full_url, base_url, same_domain_only):
            continue

        text = clean_text(node.get_text(" ", strip=True))
        if not text or len(text) < 2:
            continue

        if full_url in seen_urls:
            continue

        item = {"title": text, "url": full_url}
        seen_urls.add(full_url)

        if current_section is None:
            current_section = {"section_title": "未分类", "items": []}
            sections.append(current_section)

        current_section["items"].append(item)

    return [section for section in sections if section["items"]]


def build_output(url: str, soup: BeautifulSoup, sections: List[Dict]) -> Dict:
    page_title = clean_text(soup.title.get_text(" ", strip=True)) if soup.title else ""
    flat_items = []
    for section in sections:
        for item in section["items"]:
            flat_items.append(
                {
                    "section_title": section["section_title"],
                    "title": item["title"],
                    "url": item["url"],
                }
            )

    return {
        "source_url": url,
        "page_title": page_title,
        "section_count": len(sections),
        "link_count": len(flat_items),
        "sections": sections,
        "items": flat_items,
    }


def main() -> int:
    args = parse_args()
    html = fetch_html(args.url)
    soup = BeautifulSoup(html, "html.parser")
    sections = extract_sections(soup, args.url, args.same_domain_only)
    payload = build_output(args.url, soup, sections)

    with open(args.output, "w", encoding="utf-8") as file:
        json.dump(payload, file, ensure_ascii=False, indent=2)

    print(
        json.dumps(
            {
                "ok": True,
                "page_title": payload["page_title"],
                "section_count": payload["section_count"],
                "link_count": payload["link_count"],
                "output": args.output,
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
