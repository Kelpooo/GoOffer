import argparse
import json
import os
import re
import time
from typing import Any, Dict, List
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


DEFAULT_MODEL = "deepseek-v4-flash"
DEFAULT_BASE_URL = "https://api.deepseek.com/chat/completions"
USER_AGENT = "Mozilla/5.0"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="把已清洗的详情页正文批量提炼成题库 JSON。")
    parser.add_argument("--input-dir", required=True, help="清洗后的分组目录，例如 cleaned_pages_v2")
    parser.add_argument("--output-dir", required=True, help="提炼后的题库输出目录")
    parser.add_argument("--api-key", default=os.getenv("DEEPSEEK_API_KEY", ""), help="默认读取 DEEPSEEK_API_KEY")
    parser.add_argument("--model", default=DEFAULT_MODEL, help="模型名")
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL, help="OpenAI 兼容 chat completions 地址")
    parser.add_argument("--limit", type=int, default=0, help="只处理前 N 条，0 表示全部")
    parser.add_argument("--delay", type=float, default=0.6, help="每次模型调用间隔秒数")
    parser.add_argument("--max-chars", type=int, default=12000, help="每条正文最多送入模型的字符数")
    parser.add_argument("--batch-size", type=int, default=5, help="每次模型调用处理的题目数，默认 5")
    return parser.parse_args()


def clean_text(text: str) -> str:
    text = str(text or "").replace("\r", "\n")
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = re.sub(r"[ \t]+", " ", text)
    return text.strip()


def truncate_text(text: str, max_chars: int) -> str:
    text = clean_text(text)
    if len(text) <= max_chars:
        return text
    return text[:max_chars] + "\n\n[TRUNCATED]"


def strip_code_fences(text: str) -> str:
    stripped = text.strip()
    if stripped.startswith("```"):
        stripped = re.sub(r"^```(?:json)?\s*", "", stripped)
        stripped = re.sub(r"\s*```$", "", stripped)
    return stripped.strip()


def parse_json_response(raw_text: str) -> Dict[str, Any]:
    stripped = strip_code_fences(raw_text)
    try:
        return json.loads(stripped)
    except json.JSONDecodeError:
        start = stripped.find("{")
        end = stripped.rfind("}")
        if start != -1 and end != -1 and end > start:
            return json.loads(stripped[start : end + 1])
        raise


def build_prompt(batch_items: List[Dict[str, Any]]) -> str:
    records = []
    for idx, item in enumerate(batch_items, start=1):
        records.append(
            {
                "id": idx,
                "question_title": clean_text(item.get("question_title", "")),
                "bucket": clean_text(item.get("bucket", "")),
                "section_title": clean_text(item.get("section_title", "")),
                "page_title": clean_text(item.get("page_title", "")),
                "content_text": clean_text(item.get("content_text", "")),
            }
        )

    records_json = json.dumps(records, ensure_ascii=False, indent=2)

    return f"""你现在是一个“技术面试题库提炼器”，任务是把一批已经清洗过的面试题详情页正文，提炼成标准题库格式。

输入说明：
1. 每条记录里的 question_title 是原始题目标题，通常已经是面试题
2. bucket 和 section_title 是来源分类，可以辅助你判断技术板块
3. content_text 是题目详情正文，里面通常包含核心答案、深度解析、高频追问等内容
4. 你会一次收到多条记录，请逐条输出结构化结果

你的任务：
1. 保留并标准化题目
2. 从正文中提炼 3 到 6 条高质量 answer_points
3. 生成 2 到 4 条合理的面试 follow_ups
4. 生成 tags
5. 判断 difficulty
6. 输出严格 JSON

规则：
1. question 优先基于 question_title 标准化，不要偏离原标题含义
2. answer_points 要简洁、可读、适合题库展示
3. 不要把广告、导航、上一题下一题、推广内容写进答案
4. 不要生成原文没有依据的细节
5. tags 控制在 2 到 5 个
6. difficulty 只能是 junior / mid / senior
7. category 优先参考 bucket，但如果明显不准，可以修正
8. 必须为每一条输入记录都返回一个结果，不要漏掉
9. 结果中的 id 必须与输入 id 一致

category 可选值：
- java_base
- java_collection
- jvm
- concurrency
- spring
- mysql
- redis
- mq
- network
- os
- design_pattern
- microservice
- algorithm
- interview_misc
- uncategorized

输出 JSON 结构：
{{
  "items": [
    {{
      "id": 1,
      "question": "标准化后的题目",
      "category": "分类",
      "difficulty": "junior | mid | senior",
      "tags": ["标签1", "标签2"],
      "answer_points": [
        "答案要点1",
        "答案要点2"
      ],
      "follow_ups": [
        "追问1",
        "追问2"
      ],
      "summary": "一句简短总结，可为空字符串"
    }}
  ]
}}

最终要求：
- 只输出合法 JSON
- 不要输出 markdown 代码块
- 不要输出解释文字

输入数据：
{records_json}
"""


def call_model(api_key: str, base_url: str, model: str, prompt: str) -> str:
    if not api_key:
        raise ValueError("Missing API key. Set DEEPSEEK_API_KEY or pass --api-key.")

    payload = {
        "model": model,
        "temperature": 0.1,
        "messages": [
            {"role": "system", "content": "You extract structured interview QA and must return only valid JSON."},
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
            "User-Agent": USER_AGENT,
        },
        method="POST",
    )

    with urlopen(request, timeout=120) as response:
        body = response.read().decode("utf-8", errors="replace")
        data = json.loads(body)
        return data["choices"][0]["message"]["content"]


def normalize_list(value: Any) -> List[str]:
    if isinstance(value, list):
        return [clean_text(v) for v in value if clean_text(v)]
    if isinstance(value, str) and clean_text(value):
        return [clean_text(value)]
    return []


def normalize_record(item: Dict[str, Any], extracted: Dict[str, Any]) -> Dict[str, Any]:
    question = clean_text(extracted.get("question", "")) or clean_text(item.get("question_title", ""))
    category = clean_text(extracted.get("category", "")) or clean_text(item.get("bucket", "")) or "uncategorized"
    difficulty = clean_text(extracted.get("difficulty", "")) or "mid"
    if difficulty not in {"junior", "mid", "senior"}:
        difficulty = "mid"

    return {
        "question": question,
        "domain": "backend",
        "category": category,
        "difficulty": difficulty,
        "tags": normalize_list(extracted.get("tags", [])),
        "answer_points": normalize_list(extracted.get("answer_points", [])),
        "follow_ups": normalize_list(extracted.get("follow_ups", [])),
        "summary": clean_text(extracted.get("summary", "")),
        "source_url": clean_text(item.get("url", "")),
        "source_title": clean_text(item.get("page_title", "")),
        "section_title": clean_text(item.get("section_title", "")),
        "bucket": clean_text(item.get("bucket", "")),
        "raw_question_title": clean_text(item.get("question_title", "")),
    }


def chunk_list(items: List[Dict[str, Any]], batch_size: int) -> List[List[Dict[str, Any]]]:
    if batch_size <= 0:
        batch_size = 1
    return [items[i : i + batch_size] for i in range(0, len(items), batch_size)]


def parse_batch_items(response_payload: Dict[str, Any]) -> List[Dict[str, Any]]:
    items = response_payload.get("items", [])
    if isinstance(items, list):
        return [item for item in items if isinstance(item, dict)]
    return []


def normalize_batch_response(batch_items: List[Dict[str, Any]], extracted_items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    extracted_by_id = {}
    for item in extracted_items:
        item_id = item.get("id")
        if isinstance(item_id, int):
            extracted_by_id[item_id] = item

    normalized_records = []
    for idx, raw_item in enumerate(batch_items, start=1):
        extracted = extracted_by_id.get(idx, {})
        normalized_records.append(normalize_record(raw_item, extracted))
    return normalized_records


def load_group_files(input_dir: str) -> List[str]:
    files = []
    for filename in os.listdir(input_dir):
        if not filename.endswith(".json"):
            continue
        if filename in {"manifest.json", "failures.json"}:
            continue
        files.append(os.path.join(input_dir, filename))
    return sorted(files)


def load_group_items(path: str) -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as file:
        return json.load(file)


def write_json(path: str, data: Dict[str, Any]) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as file:
        json.dump(data, file, ensure_ascii=False, indent=2)


def main() -> int:
    args = parse_args()
    group_files = load_group_files(args.input_dir)
    os.makedirs(args.output_dir, exist_ok=True)

    total_processed = 0
    total_success = 0
    total_failures = 0
    failure_items: List[Dict[str, str]] = []
    manifest_groups: List[Dict[str, Any]] = []

    for group_path in group_files:
        payload = load_group_items(group_path)
        bucket = clean_text(payload.get("bucket", os.path.splitext(os.path.basename(group_path))[0]))
        items = payload.get("items", [])
        if args.limit > 0:
            remaining = max(args.limit - total_processed, 0)
            if remaining == 0:
                break
            items = items[:remaining]

        extracted_items: List[Dict[str, Any]] = []
        group_failures = 0

        for batch in chunk_list(items, args.batch_size):
            try:
                prepared_batch = []
                for item in batch:
                    total_processed += 1
                    item = dict(item)
                    item["content_text"] = truncate_text(item.get("content_text", ""), args.max_chars)
                    prepared_batch.append(item)

                prompt = build_prompt(prepared_batch)
                raw_response = call_model(args.api_key, args.base_url, args.model, prompt)
                extracted_payload = parse_json_response(raw_response)
                batch_extracted_items = parse_batch_items(extracted_payload)
                normalized_records = normalize_batch_response(prepared_batch, batch_extracted_items)

                for record in normalized_records:
                    extracted_items.append(record)
                    total_success += 1
                    print(f"[ok] {bucket}  {record['question']}")
            except (HTTPError, URLError, TimeoutError, ValueError, json.JSONDecodeError) as exc:
                for item in batch:
                    total_failures += 1
                    group_failures += 1
                    failure_items.append(
                        {
                            "bucket": bucket,
                            "question_title": clean_text(item.get("question_title", "")),
                            "url": clean_text(item.get("url", "")),
                            "error": str(exc),
                        }
                    )
                    print(f"[fail] {bucket}  {clean_text(item.get('question_title', ''))}  {exc}")

            if args.delay > 0:
                time.sleep(args.delay)

        output_path = os.path.join(args.output_dir, os.path.basename(group_path))
        write_json(
            output_path,
            {
                "bucket": bucket,
                "count": len(extracted_items),
                "items": extracted_items,
            },
        )
        manifest_groups.append(
            {
                "bucket": bucket,
                "count": len(extracted_items),
                "failures": group_failures,
                "file": os.path.basename(group_path),
            }
        )

        if args.limit > 0 and total_processed >= args.limit:
            break

    write_json(
        os.path.join(args.output_dir, "manifest.json"),
        {
            "group_count": len(manifest_groups),
            "processed_count": total_processed,
            "success_count": total_success,
            "failure_count": total_failures,
            "groups": manifest_groups,
        },
    )
    write_json(
        os.path.join(args.output_dir, "failures.json"),
        {
            "count": total_failures,
            "items": failure_items,
        },
    )

    print(
        json.dumps(
            {
                "ok": True,
                "processed_count": total_processed,
                "success_count": total_success,
                "failure_count": total_failures,
                "output_dir": os.path.abspath(args.output_dir),
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
