"""設定ファイル(.yaml)と環境変数(.env)の読み込み。"""

from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml

try:
    from dotenv import load_dotenv

    load_dotenv()
except Exception:  # python-dotenv 未導入でも環境変数だけで動作する
    pass

ROOT = Path(__file__).resolve().parent.parent
CONFIG_DIR = ROOT / "config"
OUTPUT_DIR = ROOT / "output"


def _load_yaml(name: str) -> dict[str, Any]:
    path = CONFIG_DIR / name
    with path.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f)


@lru_cache(maxsize=None)
def persona() -> dict[str, Any]:
    return _load_yaml("persona.yaml")


@lru_cache(maxsize=None)
def themes() -> dict[str, Any]:
    return _load_yaml("content_themes.yaml")


def env(key: str, default: str | None = None) -> str | None:
    return os.environ.get(key, default)


def gemini_api_key() -> str | None:
    return env("GEMINI_API_KEY") or None


def image_model() -> str:
    return env("GEMINI_IMAGE_MODEL", "gemini-3-pro-image-preview")


def text_model() -> str:
    return env("GEMINI_TEXT_MODEL", "gemini-3-pro")


def posts_per_run() -> int:
    raw = env("POSTS_PER_RUN")
    if raw and raw.isdigit():
        return int(raw)
    return int(persona()["schedule"].get("posts_per_day", 2))


def design() -> dict[str, Any]:
    return persona()["design"]


def step_count() -> int:
    return int(persona()["format"].get("step_count", 6))
