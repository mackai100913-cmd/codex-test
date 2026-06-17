#!/usr/bin/env python3
"""Geminiウェブ版(gemini.google.com)を自動操作して画像を作り、
「素材」フォルダへ自動保存するスクリプト（モード②・ローカル実行用）。

⚠️ 重要・必ずお読みください
  - これは「あなたのPC」で実行します（このクラウド環境では動きません）。
  - 消費者向けGeminiの自動操作は Google の利用規約に抵触する恐れがあり、
    アカウント制限のリスクがあります。自己責任でご利用ください。
    安定・安全に全自動化したい場合は API課金(モードA) を推奨します。
  - GeminiのUI変更でセレクタが合わなくなったら config/gemini_selectors.yaml を更新。

== 準備（初回のみ）==
  pip install playwright pyyaml
  playwright install chromium

== 使い方 ==
  python auto_gemini.py                # output内の全投稿の不足画像を生成
  python auto_gemini.py 2026-06-15_01  # 投稿を指定
  python auto_gemini.py --headless     # 画面非表示（初回ログイン後）
初回はブラウザが開くので、Geminiにログインしてください（プロフィールは保存され、次回以降は自動）。
生成後は自動で  python run.py --build  まで実行し、品質審査まで行います。
"""

from __future__ import annotations

import argparse
import base64
import subprocess
import sys
import time
from pathlib import Path

import yaml

from src import config
from src.image_generator import hero_prompt, step_prompt
from src.recipe_generator import _recipe_from_dict

GEMINI_URL = "https://gemini.google.com/app"
PROFILE_DIR = config.ROOT / ".gemini_profile"   # ログイン状態を保存（.gitignore済み）
SELECTORS = yaml.safe_load((config.CONFIG_DIR / "gemini_selectors.yaml").read_text(encoding="utf-8"))


# デザイン責任者の合格ラインに達するまで作り直す最大回数（1回目＋作り直し）
MAX_ATTEMPTS = 3


def load_recipe(post_dir: Path):
    import json
    return _recipe_from_dict(
        json.loads((post_dir / "recipe.json").read_text(encoding="utf-8")), seed=post_dir.name
    )


# --- 投稿ごとの「必要な画像と、そのプロンプト」一覧 ---------------------
# 各要素: (ファイル名, プロンプト, 種類, アスペクト)

def needed_images(post_dir: Path):
    recipe = load_recipe(post_dir)
    items = [("hero", hero_prompt(recipe), "hero", "9:16")]
    for i, st in enumerate(recipe.steps, start=1):
        items.append((f"step_{i}", step_prompt(recipe, st.title, st.detail), "step", "1:1"))
    return items


def _exists(assets: Path, name: str) -> bool:
    return any((assets / f"{name}{ext}").exists() for ext in (".png", ".jpg", ".jpeg", ".webp")) \
        or bool(list(assets.glob(f"{name}.*")))


# --- Playwright 操作ヘルパー -------------------------------------------

def _first(page, selectors, timeout=8000):
    """候補セレクタを上から試し、最初に見つかった要素を返す。"""
    for sel in selectors:
        try:
            el = page.wait_for_selector(sel, timeout=timeout, state="visible")
            if el:
                return el
        except Exception:
            continue
    return None


def _wait_logged_in(page):
    el = _first(page, SELECTORS["logged_in_marker"], timeout=4000)
    if el:
        return True
    print("\n🔐 Geminiにログインしてください。ログインできたらこのターミナルで Enter を押してください…")
    try:
        input()
    except EOFError:
        time.sleep(30)
    return _first(page, SELECTORS["logged_in_marker"], timeout=8000) is not None


def _send_prompt(page, prompt: str) -> bool:
    box = _first(page, SELECTORS["input_box"])
    if not box:
        print("  ⚠ 入力欄が見つかりません（gemini_selectors.yaml の input_box を更新してください）")
        return False
    box.click()
    page.keyboard.type(prompt, delay=8)
    time.sleep(0.5)
    btn = _first(page, SELECTORS["send_button"], timeout=3000)
    if btn:
        btn.click()
    else:
        page.keyboard.press("Enter")
    return True


def _candidate_images(page):
    """応答画像の候補(大きめ)を出現順で返す。"""
    out = []
    seen = set()
    for sel in SELECTORS["response_image"]:
        try:
            imgs = page.query_selector_all(sel)
        except Exception:
            imgs = []
        for el in imgs:
            try:
                box = el.bounding_box()
                if not box or box["width"] < 200 or box["height"] < 200:
                    continue
                key = (el.get_attribute("src") or "") + f"{box['x']:.0f},{box['y']:.0f}"
                if key in seen:
                    continue
                seen.add(key)
                out.append(el)
            except Exception:
                continue
    return out


def _count_images(page) -> int:
    return len(_candidate_images(page))


def _save_img(page, el, save_path: Path) -> bool:
    src = el.get_attribute("src") or ""
    try:
        if src.startswith("data:image"):
            save_path.write_bytes(base64.b64decode(src.split(",", 1)[1]))
            return True
        if src.startswith("http"):
            resp = page.request.get(src)
            if resp.ok:
                save_path.write_bytes(resp.body())
                return True
        el.screenshot(path=str(save_path))  # blob: などはスクショで代替
        return True
    except Exception:
        try:
            el.screenshot(path=str(save_path))
            return True
        except Exception:
            return False


def _grab_image(page, save_path: Path, baseline: int = 0, timeout_s: int = 120) -> bool:
    """同じチャット内で、送信前の画像枚数(baseline)より増えた=新しい画像を待って保存。"""
    deadline = time.time() + timeout_s
    while time.time() < deadline:
        cands = _candidate_images(page)
        if len(cands) > baseline:
            # 生成完了を少し待って(描画途中を避ける)、一番新しい(末尾)を取得
            time.sleep(2)
            cands = _candidate_images(page)
            if _save_img(page, cands[-1], save_path):
                return True
        time.sleep(2)
    return False


def _new_chat(page):
    btn = _first(page, SELECTORS["new_chat_button"], timeout=2500)
    if btn:
        try:
            btn.click()
            time.sleep(1.0)
        except Exception:
            pass


# --- デザイン責任者による品質チェック＋作り直しループ -------------------

def _retry_prompt(orig_prompt: str, result) -> str:
    """審査で不合格だった画像を、改善要望を添えて作り直すためのプロンプト。"""
    reqs = "\n".join(f"・{r}" for r in (result.requests or [])) or "・もっと美味しそうに、本物の写真らしく。"
    base = result.regenerate_prompt or orig_prompt
    return (
        f"今の画像はデザイン責任者の審査で {result.total}/100点（不合格）でした。"
        "同じ料理・同じ世界観のまま、次の点を必ず改善して作り直してください:\n"
        f"{reqs}\n---\n{base}"
    )


def _make_with_review(page, recipe, save_path: Path, name: str,
                      prompt: str, kind: str, aspect: str) -> bool:
    """画像を生成→デザイン責任者が審査→不合格なら作り直し。合格 or 最高得点を採用。"""
    from src.design_director import review_image

    best_score = -1
    cur_prompt = prompt
    for attempt in range(1, MAX_ATTEMPTS + 1):
        tag = "生成" if attempt == 1 else f"作り直し{attempt - 1}回目"
        print(f"  ▶ {name} を{tag}中…")
        baseline = _count_images(page)
        if not _send_prompt(page, cur_prompt):
            return False
        tmp = save_path.with_suffix(f".try{attempt}.png")
        if not _grab_image(page, tmp, baseline=baseline):
            print(f"  ⚠ {name}: 画像を自動取得できませんでした。手動で {save_path} に置いてください。")
            return best_score >= 0

        res = review_image(tmp, recipe, kind=kind, aspect=aspect)
        mark = "✅合格" if res.passed else "❌不合格"
        print(f"     デザイン責任者: {res.total}/100 {mark}（{res.engine}）")
        if res.summary:
            print(f"     講評: {res.summary}")

        # これまでで最高得点なら採用（save_path を更新）
        if res.total > best_score:
            best_score = res.total
            tmp.replace(save_path)
        else:
            tmp.unlink(missing_ok=True)

        if res.passed:
            print(f"  ✅ {name}: 合格して保存 → {save_path}")
            return True
        if attempt < MAX_ATTEMPTS:
            for r in (res.requests or [])[:4]:
                print(f"       → 改善指示: {r}")
            cur_prompt = _retry_prompt(prompt, res)
            time.sleep(2)

    print(f"  ⚠ {name}: {MAX_ATTEMPTS}回試して合格に届かず。最高得点({best_score})の画像を採用 → {save_path}")
    return True


# --- メイン処理 --------------------------------------------------------

def process(post_dirs, headless: bool):
    from playwright.sync_api import sync_playwright

    PROFILE_DIR.mkdir(exist_ok=True)
    with sync_playwright() as p:
        # playwright install したChromiumを使用（Google Chrome本体は不要）。
        # Chromeプロファイルを使いたい場合は launch_kwargs に channel="chrome" を追加。
        ctx = p.chromium.launch_persistent_context(
            user_data_dir=str(PROFILE_DIR),
            headless=headless,
            viewport={"width": 1280, "height": 900},
            args=["--disable-blink-features=AutomationControlled"],
        )
        page = ctx.new_page()
        page.goto(GEMINI_URL, wait_until="domcontentloaded")
        if not _wait_logged_in(page):
            print("ログインを確認できませんでした。中止します。")
            ctx.close()
            return

        total_made = 0

        # 全投稿・全画像を「1つの同じチャット」で連続生成する。
        print("\n💬 1つのチャットで全画像を連続生成します")
        _new_chat(page)
        page.goto(GEMINI_URL, wait_until="domcontentloaded")
        time.sleep(2.0)

        for d in post_dirs:
            assets = d / "素材"
            assets.mkdir(exist_ok=True)
            recipe = load_recipe(d)
            print(f"\n=== {d.name} ===")

            todo = [it for it in needed_images(d) if not _exists(assets, it[0])]
            for it in needed_images(d):
                if _exists(assets, it[0]):
                    print(f"  ✓ {it[0]}: 既にあるためスキップ")
            if not todo:
                continue

            for name, prompt, kind, aspect in todo:
                if _make_with_review(page, recipe, assets / f"{name}.png",
                                     name, prompt, kind, aspect):
                    total_made += 1
                time.sleep(3)   # 次の入力まで少し待つ
        ctx.close()
        print(f"\n生成完了: {total_made}枚（デザイン責任者の審査済み）")


def main():
    ap = argparse.ArgumentParser(description="Geminiウェブ自動操作で画像生成→素材保存")
    ap.add_argument("post_id", nargs="?", default=None, help="投稿ID（省略時は全件）")
    ap.add_argument("--headless", action="store_true", help="画面を表示しない")
    ap.add_argument("--no-build", action="store_true", help="生成後に build/審査をしない")
    args = ap.parse_args()

    root = config.OUTPUT_DIR
    if args.post_id:
        dirs = [root / args.post_id]
    else:
        dirs = sorted(d for d in root.glob("*") if (d / "recipe.json").exists())
    dirs = [d for d in dirs if (d / "recipe.json").exists()]
    if not dirs:
        print("対象が見つかりません。先に python run.py を実行してください。")
        return

    try:
        process(dirs, headless=args.headless)
    except ModuleNotFoundError:
        print("Playwrightが未インストールです。次を実行してください:\n"
              "  pip install playwright pyyaml\n  playwright install chromium")
        return

    if not args.no_build:
        print("\n▶ 合成と品質審査を実行します…")
        for d in dirs:
            subprocess.run([sys.executable, "run.py", "--build", d.name])


if __name__ == "__main__":
    main()
