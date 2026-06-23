"""Import current JSON question payload into the local OfferGo database."""

import argparse
import json
from pathlib import Path

from offergo_backend.database import initialize_database, upsert_questions_from_payload


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Import web_mvp question JSON into OfferGo SQLite database.")
    parser.add_argument(
        "--input",
        default=str(Path(__file__).resolve().parent.parent / "web_mvp" / "data" / "questions.json"),
        help="Path to questions.json",
    )
    parser.add_argument(
        "--db",
        default=str(Path(__file__).resolve().parent.parent / ".runtime" / "offergo.db"),
        help="Path to sqlite db",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    input_path = Path(args.input)
    db_path = Path(args.db)

    with input_path.open("r", encoding="utf-8") as file:
        payload = json.load(file)

    initialize_database(db_path)
    count = upsert_questions_from_payload(db_path, payload)
    print(json.dumps({"ok": True, "imported": count, "db": str(db_path)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
