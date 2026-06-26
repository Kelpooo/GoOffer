"""Centralized runtime configuration for OfferGo."""

from dataclasses import dataclass
import os
from pathlib import Path


@dataclass(frozen=True)
class Settings:
    base_dir: Path
    web_dir: Path
    runtime_dir: Path
    prompt_file: Path
    host: str
    port: int
    max_upload_size: int
    deepseek_api_url: str
    visitor_cookie_name: str
    visitor_stats_path: Path
    deepseek_model: str
    storage_mode: str
    app_db_path: Path


def load_dotenv_file(env_path: Path) -> None:
    if not env_path.is_file():
        return

    try:
        content = env_path.read_text(encoding="utf-8-sig")
    except OSError:
        return

    for raw_line in content.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue

        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip()
        if not key or key in os.environ:
            continue

        quoted = len(value) >= 2 and value[0] == value[-1] and value[0] in {'"', "'"}
        if not quoted and "#" in value:
            value = value.split("#", 1)[0].rstrip()
        if quoted:
            value = value[1:-1]
        os.environ[key] = value


def load_settings() -> Settings:
    base_dir = Path(__file__).resolve().parent.parent
    runtime_dir = base_dir / ".runtime"
    load_dotenv_file(base_dir / ".env")
    return Settings(
        base_dir=base_dir,
        web_dir=base_dir / "web_mvp",
        runtime_dir=runtime_dir,
        prompt_file=base_dir / "prompt_templates.json",
        host=os.environ.get("RESUME_REVIEW_HOST", "0.0.0.0"),
        port=int(os.environ.get("PORT", os.environ.get("RESUME_REVIEW_PORT", "8000"))),
        max_upload_size=5 * 1024 * 1024,
        deepseek_api_url=os.environ.get("DEEPSEEK_API_URL", "https://api.deepseek.com/chat/completions"),
        visitor_cookie_name=os.environ.get("VISITOR_COOKIE_NAME", "offergo_vid"),
        visitor_stats_path=Path(os.environ.get("VISITOR_STATS_PATH", runtime_dir / "visitor_stats.json")),
        deepseek_model=os.environ.get("DEEPSEEK_MODEL", "deepseek-chat"),
        storage_mode=os.environ.get("OFFERGO_STORAGE_MODE", "file").strip().lower() or "file",
        app_db_path=Path(os.environ.get("OFFERGO_DB_PATH", runtime_dir / "offergo.db")),
    )
