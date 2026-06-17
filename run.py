#!/usr/bin/env python3
"""グルメTikTok 自動投稿パッケージ生成 CLI。

通常生成:
    python run.py                # 今日の投稿を設定数だけ生成
    python run.py --count 3      # 件数指定
    python run.py --date 2026-06-20

素材（Geminiアプリで自作した画像）からの再合成:
    python run.py --build            # output内の全投稿を素材から作り直す
    python run.py --build 2026-06-15_01   # 指定投稿だけ作り直す
"""

from __future__ import annotations

import argparse
from datetime import date

from src import config
from src.packager import rebuild_package
from src.pipeline import run


def _review(post_id: str | None) -> None:
    """素材のメイン写真(hero)をデザイン責任者が審査する。"""
    import json as _json
    from pathlib import Path

    from src.design_director import review_image
    from src.image_generator import _find_asset
    from src.recipe_generator import _recipe_from_dict

    root = config.OUTPUT_DIR
    targets = ([root / post_id] if post_id
               else sorted(p for p in root.glob("*") if (p / "recipe.json").exists()))
    if not targets:
        print("対象が見つかりません。先に python run.py で生成してください。")
        return
    for d in targets:
        rj = d / "recipe.json"
        if not rj.exists():
            continue
        recipe = _recipe_from_dict(_json.loads(rj.read_text(encoding="utf-8")), seed=d.name)
        assets = d / "素材"
        # 審査対象: 素材のhero。無ければ合成済みの表紙。
        hero = None
        for base in ("hero", "hero1", "01_hero"):
            for ext in (".jpg", ".jpeg", ".png", ".webp"):
                if (assets / f"{base}{ext}").exists():
                    hero = assets / f"{base}{ext}"
                    break
            if hero:
                break
        if hero is None:
            hero = next(iter(assets.glob("hero.*")), None) if assets.exists() else None
        if hero is None:
            print(f"⚠ {d.name}: 素材フォルダに hero 画像がありません。")
            continue

        result = review_image(hero, recipe)
        report = result.report(title=f"{recipe.title_top}{recipe.title_main}")
        print("\n" + report)
        (d / "審査結果.txt").write_text(report + "\n", encoding="utf-8")
        print(f"\n→ 審査結果を保存: {d / '審査結果.txt'}")


def _build(post_id: str | None) -> None:
    root = config.OUTPUT_DIR
    if post_id:
        targets = [root / post_id]
    else:
        targets = sorted(p for p in root.glob("*") if (p / "recipe.json").exists())
    if not targets:
        print("対象の投稿が見つかりません。先に python run.py で生成してください。")
        return
    for d in targets:
        if not (d / "recipe.json").exists():
            print(f"⚠ {d.name}: recipe.json が無いためスキップ")
            continue
        assets = list((d / "素材").glob("*")) if (d / "素材").exists() else []
        rebuild_package(d)
        print(f"🔁 {d.name}: 素材{len(assets)}枚を反映して再合成しました → {d}")
        # 合成後にメイン写真を自動審査（品質担保）
        if assets:
            _review(d.name)


def main() -> None:
    parser = argparse.ArgumentParser(description="グルメTikTok自動コンテンツ生成")
    parser.add_argument("--count", type=int, default=None, help="生成する投稿数")
    parser.add_argument("--date", type=str, default=None, help="対象日 YYYY-MM-DD")
    parser.add_argument("--build", nargs="?", const="__all__", default=None,
                        help="素材フォルダの画像から再合成（投稿IDを指定可）")
    parser.add_argument("--review", nargs="?", const="__all__", default=None,
                        help="デザイン責任者が素材のメイン写真を審査（投稿IDを指定可）")
    args = parser.parse_args()

    if args.review is not None:
        _review(None if args.review == "__all__" else args.review)
        return

    if args.build is not None:
        _build(None if args.build == "__all__" else args.build)
        return

    target = date.fromisoformat(args.date) if args.date else None
    run(n=args.count, target_date=target)


if __name__ == "__main__":
    main()
