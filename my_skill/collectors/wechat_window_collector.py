import ctypes
import json
import time
from pathlib import Path
from tkinter import Tk


user32 = ctypes.windll.user32

VK_CONTROL = 0x11
VK_A = 0x41
VK_C = 0x43
VK_PRIOR = 0x21
KEYEVENTF_KEYUP = 0x0002


def _press_key(vk_code: int):
    user32.keybd_event(vk_code, 0, 0, 0)
    time.sleep(0.03)
    user32.keybd_event(vk_code, 0, KEYEVENTF_KEYUP, 0)


def _press_combo(*vk_codes: int):
    for code in vk_codes:
        user32.keybd_event(code, 0, 0, 0)
        time.sleep(0.03)
    for code in reversed(vk_codes):
        user32.keybd_event(code, 0, KEYEVENTF_KEYUP, 0)
        time.sleep(0.03)


def _read_clipboard_text() -> str:
    root = Tk()
    root.withdraw()
    try:
        text = root.clipboard_get()
    except Exception:
        text = ""
    finally:
        root.destroy()
    return text


def _normalize_block(text: str) -> str:
    lines = [line.rstrip() for line in text.replace("\r\n", "\n").split("\n")]
    cleaned = [line for line in lines if line.strip()]
    return "\n".join(cleaned).strip()


def _find_line_overlap(existing: str, incoming: str) -> int:
    existing_lines = existing.splitlines()
    incoming_lines = incoming.splitlines()
    max_overlap = min(len(existing_lines), len(incoming_lines), 80)
    for size in range(max_overlap, 0, -1):
        if existing_lines[-size:] == incoming_lines[:size]:
            return size
    return 0


def _merge_blocks(blocks: list[str]) -> str:
    merged_lines: list[str] = []
    for block in blocks:
        normalized = _normalize_block(block)
        if not normalized:
            continue
        block_lines = normalized.splitlines()
        if not merged_lines:
            merged_lines.extend(block_lines)
            continue
        overlap = _find_line_overlap("\n".join(merged_lines), normalized)
        if overlap > 0:
            merged_lines.extend(block_lines[overlap:])
        elif normalized not in "\n".join(merged_lines):
            merged_lines.extend([""] + block_lines)
    return "\n".join(merged_lines).strip()


def _countdown(seconds: int):
    for remaining in range(seconds, 0, -1):
        print(f"Switch to WeChat and focus the message area. Starting in {remaining}s...")
        time.sleep(1)


def collect_wechat_window_chat(
    output_path: str,
    rounds: int = 10,
    delay: float = 3.5,
    startup_delay: int = 5,
    pageup_presses: int = 8,
):
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    raw_output = output.with_name(f"{output.stem}.raw.json")

    _countdown(startup_delay)

    blocks: list[str] = []
    seen = set()

    for index in range(rounds):
        _press_combo(VK_CONTROL, VK_A)
        time.sleep(0.2)
        _press_combo(VK_CONTROL, VK_C)
        time.sleep(delay)

        text = _normalize_block(_read_clipboard_text())
        if text and text not in seen:
            seen.add(text)
            blocks.append(text)
            print(f"[round {index + 1}/{rounds}] captured {len(text)} chars")
        else:
            print(f"[round {index + 1}/{rounds}] no new text captured")

        for _ in range(pageup_presses):
            _press_key(VK_PRIOR)
            time.sleep(0.08)
        time.sleep(0.5)

    merged = _merge_blocks(blocks)
    output.write_text(merged, encoding="utf-8")
    raw_output.write_text(
        json.dumps({"blocks": blocks}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    return {
        "output_path": str(output),
        "raw_output_path": str(raw_output),
        "block_count": len(blocks),
        "merged_chars": len(merged),
    }
