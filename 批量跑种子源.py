import argparse
import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent
SEED_FILE = ROOT / "seed_sources.json"
SKIP_FILES = {"manifest.json", "failures.json"}


def slug_path(*parts):
    path = ROOT
    for part in parts:
        path /= part
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def run_command(args):
    print(">", " ".join(str(item) for item in args))
    result = subprocess.run(args, cwd=ROOT)
    if result.returncode != 0:
        raise SystemExit(result.returncode)


def load_seeds():
    with SEED_FILE.open("r", encoding="utf-8") as file:
        return json.load(file)


def has_json_results(path):
    if not path.exists():
        return False
    if path.is_file():
        return path.suffix.lower() == ".json" and path.name not in SKIP_FILES and path.stat().st_size > 0
    return any(
        item.is_file() and item.suffix.lower() == ".json" and item.name not in SKIP_FILES and item.stat().st_size > 0
        for item in path.glob("*.json")
    )


def group_domain(group_name):
    mapping = {
        "frontend_articles": "frontend",
        "backend_articles": "backend",
        "ai_articles": "ai_app",
        "testing_articles": "testing",
        "algorithm_articles": "algorithm",
        "ops_articles": "ops",
        "cs_basic_articles": "cs_basic",
    }
    return mapping.get(group_name)


def run_article_group(group_name, items, model, base_url, max_chars, refresh):
    domain = group_domain(group_name)
    if not domain:
        print(f"[skip] unsupported article group: {group_name}")
        return

    for item in items:
        output = slug_path("question_bank", domain, "processed", f"{item['name']}.json")
        raw_output = slug_path("question_bank", domain, "raw", f"{item['name']}_raw.txt")
        if not refresh and has_json_results(output):
            print(f"[skip] existing article result: {item['name']}")
            continue
        command = [
            sys.executable,
            str(ROOT / "extract_questions.py"),
            "--url",
            item["url"],
            "--title",
            item["title"],
            "--output",
            str(output),
            "--raw-output",
            str(raw_output),
            "--model",
            model,
            "--fetch-mode",
            item.get("fetch_mode", "auto"),
            "--max-chars",
            str(max_chars),
        ]
        if base_url:
            command.extend(["--base-url", base_url])
        run_command(command)


def run_backend_directory(items, model, base_url, limit, batch_size, refresh):
    for item in items:
        name = item["name"]
        link_json = slug_path("question_bank", "backend", "directories", f"{name}_links.json")
        raw_dir = ROOT / "question_bank" / "backend" / f"{name}_raw_pages"
        clean_dir = ROOT / "question_bank" / "backend" / f"{name}_cleaned_pages"
        output_dir = ROOT / "question_bank" / "backend" / f"{name}_extracted_questions"

        if not refresh and has_json_results(output_dir):
            print(f"[skip] existing directory result: {name}")
            continue

        command = [
            sys.executable,
            str(ROOT / "爬取跳转目录网址.py"),
            "--url",
            item["url"],
            "--output",
            str(link_json),
        ]
        if item.get("same_domain_only", False):
            command.append("--same-domain-only")
        run_command(command)

        crawl_command = [
            sys.executable,
            str(ROOT / "批量爬取详情页正文.py"),
            "--input",
            str(link_json),
            "--output-dir",
            str(raw_dir),
            "--delay",
            "0",
        ]
        if item.get("same_domain_only", False):
            crawl_command.append("--same-domain-only")
        if limit > 0:
            crawl_command.extend(["--limit", str(limit)])
        run_command(crawl_command)

        clean_command = [
            sys.executable,
            str(ROOT / "批量爬取详情页正文.py"),
            "--clean-existing-dir",
            str(raw_dir),
            "--output-dir",
            str(clean_dir),
        ]
        run_command(clean_command)

        extract_command = [
            sys.executable,
            str(ROOT / "批量提炼题库.py"),
            "--input-dir",
            str(clean_dir),
            "--output-dir",
            str(output_dir),
            "--model",
            model,
            "--batch-size",
            str(batch_size),
            "--delay",
            "0",
        ]
        if base_url:
            extract_command.extend(["--base-url", base_url])
        if limit > 0:
            extract_command.extend(["--limit", str(limit)])
        run_command(extract_command)


def main():
    parser = argparse.ArgumentParser(description="批量跑预设种子源，自动抓取并提炼题库。")
    parser.add_argument("--groups", default="frontend_articles,backend_articles,backend_directories,ai_articles", help="逗号分隔的分组名")
    parser.add_argument("--model", default="deepseek-chat")
    parser.add_argument("--base-url", default="https://api.deepseek.com/chat/completions")
    parser.add_argument("--max-chars", type=int, default=18000)
    parser.add_argument("--directory-limit", type=int, default=80, help="目录型站点最多抓多少详情页；80 是速度和题量平衡值")
    parser.add_argument("--batch-size", type=int, default=8, help="批量提炼题库时每次送给模型的文章数")
    parser.add_argument("--refresh", action="store_true")
    args = parser.parse_args()

    seeds = load_seeds()
    selected = [group.strip() for group in args.groups.split(",") if group.strip()]

    for group in selected:
        items = seeds.get(group, [])
        if not items:
            print(f"[skip] 未找到分组: {group}")
            continue
        print(f"\n=== running group: {group} ({len(items)}) ===")
        if group == "backend_directories":
            run_backend_directory(
                items=items,
                model=args.model,
                base_url=args.base_url,
                limit=args.directory_limit,
                batch_size=args.batch_size,
                refresh=args.refresh,
            )
        else:
            run_article_group(
                group_name=group,
                items=items,
                model=args.model,
                base_url=args.base_url,
                max_chars=args.max_chars,
                refresh=args.refresh,
            )

    print("\nAll selected seed groups completed.")


if __name__ == "__main__":
    main()
