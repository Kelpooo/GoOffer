import argparse
import json
from pathlib import Path


def try_repair_mojibake(text: str) -> str:
    candidates = [text]
    for src_enc in ("gbk", "gb18030"):
        try:
            repaired = text.encode(src_enc, errors="strict").decode("utf-8", errors="strict")
            candidates.append(repaired)
        except Exception:
            pass

    def score(value: str) -> tuple[int, int]:
        bad = value.count("\ufffd") + value.count("?")
        good = sum(1 for ch in value if "\u4e00" <= ch <= "\u9fff")
        return (good, -bad)

    return max(candidates, key=score)


def normalize_line(line: str) -> str:
    line = try_repair_mojibake(line.strip())
    line = line.replace("\u2005", " ").replace("\xa0", " ")
    return line.strip()


def merge_chunk_lines(chunks: list[dict]) -> list[str]:
    all_lines: list[str] = []
    seen_windows: set[tuple[str, ...]] = set()

    for chunk in chunks:
        raw_text = chunk.get("text", "")
        lines = [normalize_line(line) for line in raw_text.splitlines()]
        lines = [line for line in lines if line]
        if not lines:
            continue

        # dedupe repeated sliding-window captures
        fingerprint = tuple(lines[:20] + ["..."] + lines[-20:] if len(lines) > 40 else lines)
        if fingerprint in seen_windows:
            continue
        seen_windows.add(fingerprint)

        if not all_lines:
            all_lines.extend(lines)
            continue

        overlap = 0
        max_overlap = min(len(all_lines), len(lines), 120)
        for size in range(max_overlap, 0, -1):
            if all_lines[-size:] == lines[:size]:
                overlap = size
                break
        all_lines.extend(lines[overlap:])

    return all_lines


def lines_to_turns(lines: list[str]) -> list[dict]:
    turns: list[dict] = []
    current_speaker = None
    buffer: list[str] = []

    def flush():
        nonlocal buffer, current_speaker
        if current_speaker and buffer:
            turns.append(
                {
                    "speaker": current_speaker,
                    "text": "\n".join(buffer).strip(),
                }
            )
        buffer = []

    for line in lines:
        if line.endswith(":") or line.endswith("："):
            flush()
            current_speaker = line[:-1].strip()
            continue

        if current_speaker is None:
            # skip stray lines before first speaker label
            continue

        buffer.append(line)

    flush()
    return turns


def save_outputs(source_path: Path, merged_lines: list[str], turns: list[dict], output_dir: Path | None = None):
    base = source_path.with_suffix("")
    target_dir = output_dir if output_dir is not None else source_path.parent
    target_dir.mkdir(parents=True, exist_ok=True)
    cleaned_txt = target_dir / f"{base.name}.cleaned.txt"
    cleaned_json = target_dir / f"{base.name}.cleaned.json"

    cleaned_txt.write_text("\n".join(merged_lines), encoding="utf-8")
    cleaned_json.write_text(
        json.dumps(
            {
                "source_file": str(source_path),
                "line_count": len(merged_lines),
                "turn_count": len(turns),
                "turns": turns,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    return cleaned_txt, cleaned_json


def main():
    parser = argparse.ArgumentParser(description="Normalize captured WeChat chat export")
    parser.add_argument("--input", required=True, help="Path to exported JSON capture")
    parser.add_argument("--output-dir", default=None, help="Optional output directory for cleaned files")
    args = parser.parse_args()

    source_path = Path(args.input)
    payload = json.loads(source_path.read_text(encoding="utf-8"))
    chunks = payload.get("chunks", [])
    merged_lines = merge_chunk_lines(chunks)
    turns = lines_to_turns(merged_lines)
    output_dir = Path(args.output_dir) if args.output_dir else None
    cleaned_txt, cleaned_json = save_outputs(source_path, merged_lines, turns, output_dir=output_dir)

    print(
        json.dumps(
            {
                "cleaned_txt": str(cleaned_txt),
                "cleaned_json": str(cleaned_json),
                "line_count": len(merged_lines),
                "turn_count": len(turns),
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
