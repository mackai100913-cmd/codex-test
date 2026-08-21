"""アップロード用パッケージを書き出す。

各投稿ごとに output/<post_id>/ を作り、
- 表紙画像 / レシピカード画像
- caption.txt（材料・手順・ハッシュタグの全文 ＝ コピペでそのまま投稿）
- post.json（メタ情報） / recipe.json（レシピ全文・再合成用）
- README.txt（アップロード手順）
- 画像作成ガイド.txt（Geminiアプリ用プロンプト）
- 素材/（← ユーザーがGeminiアプリで作った画像を置くフォルダ）
を生成する。
"""

from __future__ import annotations

import json
from dataclasses import asdict
from datetime import date
from pathlib import Path

from . import config
from .caption import build_caption
from .content_planner import PostPlan
from .image_generator import generate_post_images, hero_prompt, steps_grid_prompt
from .recipe_generator import Recipe

ASSET_DIRNAME = "素材"


def _write_recipe_json(post_dir: Path, recipe: Recipe) -> None:
    (post_dir / "recipe.json").write_text(
        json.dumps(asdict(recipe), ensure_ascii=False, indent=2), encoding="utf-8"
    )


def _write_image_guide(post_dir: Path, recipe: Recipe) -> None:
    """Geminiアプリに貼り付ける画像生成プロンプト一覧を書き出す。"""
    lines = [
        f"=== 画像作成ガイド: {recipe.title_top}{recipe.title_main} ===",
        "",
        "Geminiアプリ（gemini.google.com / スマホアプリ）に、下の【プロンプト】を",
        "1つずつ貼り付けて画像を作り、保存したら指定のファイル名にして",
        f"このフォルダの「{ASSET_DIRNAME}」に入れてください。",
        "全部入れたら  python run.py --build  を実行すると完成画像になります。",
        "",
        "画像は【2枚だけ】作ればOKです（文字は入れない。文字は合成時に綺麗に入ります）。",
        "",
        "------------------------------------------------------------",
        "① メイン写真   → 保存名: hero.jpg",
        "【プロンプト】",
        hero_prompt(recipe),
        "",
        "------------------------------------------------------------",
        "② 6工程グリッド（1枚に6コマまとめて）→ 保存名: steps.jpg",
        "【プロンプト】",
        steps_grid_prompt(recipe),
        "",
        "------------------------------------------------------------",
        "※ ファイル名は hero と steps（拡張子は .jpg .png どれでもOK）",
        "※ steps は『縦3段×横2列・左上から1〜6』の並びにしてください（合成時に6分割します）",
        "※ 画像が無い分はダミー画像のまま合成されます（後から差し替え可）",
        "※ 旧方式（step_1〜6を個別）も使えます",
    ]
    (post_dir / "画像作成ガイド.txt").write_text("\n".join(lines), encoding="utf-8")


def _write_caption_meta(post_dir: Path, plan: PostPlan, recipe: Recipe, images: list[Path]) -> None:
    (post_dir / "caption.txt").write_text(build_caption(recipe), encoding="utf-8")
    meta = {
        "post_id": plan.post_id,
        "dish": f"{recipe.title_top}{recipe.title_main}",
        "scheduled_time_jst": plan.scheduled_time_jst,
        "time": recipe.time,
        "cost": recipe.cost,
        "difficulty": recipe.difficulty,
        "hashtags": recipe.hashtags,
        "images": [p.name for p in images],
    }
    (post_dir / "post.json").write_text(
        json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    instructions = (
        f"=== {plan.post_id} アップロード手順 ===\n\n"
        f"投稿推奨時刻(JST): {plan.scheduled_time_jst}\n\n"
        "1. TikTokアプリ → ＋ → 「写真」を選択\n"
        "2. slide_01_cover（表紙）→ slide_02_recipe（レシピ）の順で追加\n"
        "3. caption.txt の中身を本文にコピペ（ハッシュタグ込み）\n"
        "4. カバーは slide_01 を選択\n"
        "5. 推奨時刻に投稿（または予約投稿）\n"
    )
    (post_dir / "README.txt").write_text(instructions, encoding="utf-8")


def build_package(plan: PostPlan, recipe: Recipe, root: Path | None = None) -> Path:
    root = root or config.OUTPUT_DIR
    post_dir = root / plan.post_id
    post_dir.mkdir(parents=True, exist_ok=True)

    assets_dir = post_dir / ASSET_DIRNAME
    assets_dir.mkdir(exist_ok=True)

    _write_recipe_json(post_dir, recipe)
    _write_image_guide(post_dir, recipe)

    images = generate_post_images(plan, recipe, post_dir, assets_dir=assets_dir)
    _write_caption_meta(post_dir, plan, recipe, images)
    return post_dir


def rebuild_package(post_dir: Path) -> Path:
    """既存の recipe.json と 素材/ から、完成画像を作り直す（--build）。"""
    from .recipe_generator import _recipe_from_dict

    data = json.loads((post_dir / "recipe.json").read_text(encoding="utf-8"))
    recipe = _recipe_from_dict(data, seed=post_dir.name)
    recipe.hashtags = data.get("hashtags", recipe.hashtags)

    assets_dir = post_dir / ASSET_DIRNAME
    plan = PostPlan(post_id=post_dir.name, dish_idea="", scheduled_time_jst="", seed=post_dir.name)
    images = generate_post_images(plan, recipe, post_dir, assets_dir=assets_dir)
    _write_caption_meta(post_dir, plan, recipe, images)
    return post_dir


def write_calendar(plans: list[PostPlan], recipes: list[Recipe], target_date: date,
                   root: Path | None = None) -> Path:
    root = root or config.OUTPUT_DIR
    root.mkdir(parents=True, exist_ok=True)
    lines = [f"# 投稿カレンダー {target_date.isoformat()}", ""]
    for plan, recipe in zip(plans, recipes):
        lines += [
            f"## {plan.scheduled_time_jst}  {recipe.title_top}{recipe.title_main}",
            f"- フォルダ: `output/{plan.post_id}/`",
            f"- 調理時間: {recipe.time} / 費用: {recipe.cost} / 難易度: {recipe.difficulty}",
            f"- タグ: {' '.join(recipe.hashtags)}",
            "",
        ]
    path = root / f"calendar_{target_date.isoformat()}.md"
    path.write_text("\n".join(lines), encoding="utf-8")
    return path
