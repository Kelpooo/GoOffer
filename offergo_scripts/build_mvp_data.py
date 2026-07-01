import json
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent
OUTPUT = BASE_DIR / "web_mvp" / "data" / "questions.json"

SKIP_FILES = {"manifest.json", "failures.json"}

DOMAIN_META = {
    "frontend": {"section": "前端", "default_category": "other"},
    "backend": {"section": "后端", "default_category": "uncategorized"},
    "ai_app": {"section": "AI 应用开发", "default_category": "other"},
    "testing": {"section": "测试开发", "default_category": "other"},
    "algorithm": {"section": "算法工程师", "default_category": "other"},
    "ops": {"section": "运维 / 云原生", "default_category": "other"},
    "cs_basic": {"section": "计算机基础", "default_category": "other"},
}


def load_json(path: Path):
    with path.open("r", encoding="utf-8") as file:
        return json.load(file)


def normalize_text(value):
    return str(value or "").strip()


def normalize_list(values):
    if isinstance(values, list):
        return [normalize_text(item) for item in values if normalize_text(item)]
    if normalize_text(values):
        return [normalize_text(values)]
    return []


def processed_records(domain):
    records = []
    source_dir = BASE_DIR / "question_bank" / domain / "processed"
    if not source_dir.exists():
        return records

    meta = DOMAIN_META[domain]
    for path in sorted(source_dir.glob("*.json")):
        if path.name in SKIP_FILES:
            continue
        payload = load_json(path)
        for index, item in enumerate(payload.get("questions", []), start=1):
            question = normalize_text(item.get("question"))
            if not question:
                continue
            records.append(
                {
                    "id": f"{domain}-{path.stem}-{index}",
                    "domain": domain,
                    "section": meta["section"],
                    "question": question,
                    "category": normalize_text(item.get("category")) or meta["default_category"],
                    "difficulty": normalize_text(item.get("difficulty")) or "mid",
                    "tags": normalize_list(item.get("tags")),
                    "answerPoints": normalize_list(item.get("answer_points")),
                    "followUps": normalize_list(item.get("follow_ups")),
                    "summary": normalize_text(item.get("summary")),
                    "sourceTitle": normalize_text(payload.get("source_title")) or path.stem,
                    "sourceUrl": "",
                }
            )
    return records


def directory_records(domain):
    records = []
    meta = DOMAIN_META[domain]
    domain_root = BASE_DIR / "question_bank" / domain

    for extracted_dir in sorted(domain_root.glob("*extracted_questions*")):
        if not extracted_dir.is_dir():
            continue
        for path in sorted(extracted_dir.glob("*.json")):
            if path.name in SKIP_FILES:
                continue
            payload = load_json(path)
            for index, item in enumerate(payload.get("items", []), start=1):
                question = normalize_text(item.get("question"))
                if not question:
                    continue
                records.append(
                    {
                        "id": f"{domain}-{extracted_dir.name}-{path.stem}-{index}",
                        "domain": domain,
                        "section": meta["section"],
                        "question": question,
                        "category": normalize_text(item.get("category")) or normalize_text(item.get("bucket")) or meta["default_category"],
                        "difficulty": normalize_text(item.get("difficulty")) or "mid",
                        "tags": normalize_list(item.get("tags")),
                        "answerPoints": normalize_list(item.get("answer_points")),
                        "followUps": normalize_list(item.get("follow_ups")),
                        "summary": normalize_text(item.get("summary")),
                        "sourceTitle": normalize_text(item.get("source_title")) or path.stem,
                        "sourceUrl": normalize_text(item.get("source_url")),
                    }
                )
    return records


def dedupe_records(records):
    seen = set()
    result = []
    for record in records:
        key = (
            record["domain"],
            record["question"].strip().lower(),
        )
        if key in seen:
            continue
        seen.add(key)
        result.append(record)
    return result


def domain_groups(records):
    groups = {}
    for record in records:
        groups.setdefault(record["domain"], {}).setdefault(record["category"], 0)
        groups[record["domain"]][record["category"]] += 1
    return groups


def main():
    records = []
    for domain in ["frontend", "backend", "ai_app", "testing", "algorithm", "ops", "cs_basic"]:
        records.extend(processed_records(domain))
    for domain in ["frontend", "backend", "ops", "cs_basic"]:
        records.extend(directory_records(domain))
    records = dedupe_records(records)

    payload = {
        "meta": {
            "total": len(records),
            "domains": domain_groups(records),
        },
        "questions": records,
    }
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT.open("w", encoding="utf-8") as file:
        json.dump(payload, file, ensure_ascii=False, indent=2)
    print(json.dumps(payload["meta"], ensure_ascii=False))


if __name__ == "__main__":
    main()
