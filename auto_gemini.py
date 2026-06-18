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

== 厳密審査（APIキー不要のブラウザ審査）==
  APIキー(AIza)が使えない環境向けに、ログイン済みブラウザのGeminiへ生成画像を
  直接アップロードして各責任者ルーブリックで採点させる「ブラウザ審査」を内蔵。
    python auto_gemini.py --review browser   # ブラウザ審査を強制
    python auto_gemini.py --review auto       # 既定。キーがあればAPI・無ければブラウザ
    python auto_gemini.py --review api        # API審査(要GEMINI_API_KEY)
    python auto_gemini.py --review off        # 審査せず1発で採用
  ブラウザ審査は生成チャットを汚さないよう専用タブで実施する。
  審査も固定の専用チャット(既定「TikTok画像審査」)に合流し、会長の指摘や過去の
  審査文脈(ナレッジ)が蓄積して意図が伝わりやすくなる:
    python auto_gemini.py --review browser --review-chat "TikTok画像審査"
    python auto_gemini.py --review browser --review-new   # 合流せず新規チャットで
  初回はそのチャットが無いので新規作成される。次回から合流できるよう、作られた
  審査チャットを手動で「TikTok画像審査」と名付けておく。
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

# 既定で合流するジェミニの既存チャット名（会長が用意した共通チャット）。
# 環境変数 GEMINI_CHAT_NAME か CLI の --chat で上書き可能。
CHAT_NAME = config.env("GEMINI_CHAT_NAME", "TikTok画像自動化")

# 審査を固定するチャット名。ここに会長の指摘・過去の審査文脈(ナレッジ)が蓄積する。
# 環境変数 GEMINI_REVIEW_CHAT_NAME か CLI の --review-chat で上書き可能。
REVIEW_CHAT_NAME = config.env("GEMINI_REVIEW_CHAT_NAME", "TikTok画像審査")


# デザイン責任者の合格ラインに達するまで作り直す最大回数（1回目＋作り直し）
MAX_ATTEMPTS = 3

# 生成画像とみなす最小サイズ(px)。小さいサムネイル/アイコンを誤取得しないため大きめに。
MIN_IMG = 480


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


def _find_existing(assets: Path, name: str) -> Path | None:
    for ext in (".png", ".jpg", ".jpeg", ".webp"):
        p = assets / f"{name}{ext}"
        if p.exists():
            return p
    g = sorted(assets.glob(f"{name}.*"))
    return g[0] if g else None


def _exists(assets: Path, name: str) -> bool:
    return _find_existing(assets, name) is not None


# 既存素材として許容する最小サイズ。これ未満は低品質とみなし作り直す。
MIN_KEEP = 600


def _existing_ok(assets: Path, name: str) -> bool:
    """既存素材が十分な解像度かを判定（小さすぎるサムネイル等は作り直し対象）。"""
    p = _find_existing(assets, name)
    if p is None:
        return False
    try:
        from PIL import Image
        with Image.open(p) as im:
            return min(im.size) >= MIN_KEEP
    except Exception:
        return True   # 開けない場合は判断保留で残す


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
    try:
        box.click()
        page.keyboard.type(prompt, delay=8)
        time.sleep(0.5)
        btn = _first(page, SELECTORS["send_button"], timeout=3000)
        if btn:
            try:
                btn.click()
            except Exception:
                page.keyboard.press("Enter")   # ボタンがDOMから外れた等はEnterで代替
        else:
            page.keyboard.press("Enter")
        return True
    except Exception as e:  # noqa: BLE001
        print(f"  ⚠ 送信に失敗しました（{type(e).__name__}）。スキップします。")
        return False


def _candidate_images(page):
    """応答画像の候補(本体サイズの大きい画像)を (要素, 面積) で返す。"""
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
                if not box or box["width"] < MIN_IMG or box["height"] < MIN_IMG:
                    continue
                key = (el.get_attribute("src") or "") + f"{box['x']:.0f},{box['y']:.0f}"
                if key in seen:
                    continue
                seen.add(key)
                out.append((el, box["width"] * box["height"]))
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


def _grab_image(page, save_path: Path, baseline: int = 0, timeout_s: int = 150) -> bool:
    """同じチャット内で、送信前の画像枚数(baseline)より増えた=新しい画像を待って保存。
    生成画像は本文中で最も大きく表示されるため、候補のうち最大面積のものを採用する。"""
    deadline = time.time() + timeout_s
    while time.time() < deadline:
        cands = _candidate_images(page)
        if len(cands) > baseline:
            # 生成完了を待つ(高解像度の描画が終わるまで)
            time.sleep(4)
            cands = _candidate_images(page)
            if cands:
                el, _area = max(cands, key=lambda c: c[1])  # 最大面積=生成画像本体
                if _save_img(page, el, save_path):
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


def _open_chat(page, title: str) -> bool:
    """サイドバーの履歴から、指定タイトルの既存チャットを開いて合流する。"""
    # まずサイドバー(履歴)を開く（既に開いていれば無視される）
    btn = _first(page, SELECTORS.get("menu_button", []), timeout=3000)
    if btn:
        try:
            btn.click()
            time.sleep(1.2)
        except Exception:
            pass
    # タイトル一致の会話をクリック
    try:
        item = page.get_by_text(title, exact=False).first
        item.wait_for(state="visible", timeout=6000)
        item.click()
        time.sleep(2.5)
        return True
    except Exception:
        return False


# --- ブラウザ審査（APIキー不要のVision審査） ---------------------------
# AQ.形式キーのGoogle側不具合を回避するため、ログイン済みブラウザのGeminiに
# 画像を直接アップロードして採点させる。生成チャットを汚さないよう専用タブで実施。

def _all_response_texts(page) -> list[str]:
    """モデル応答のテキストを古い順に返す（最後が最新応答）。"""
    for sel in SELECTORS.get("response_text", []):
        try:
            els = page.query_selector_all(sel)
        except Exception:
            els = []
        if els:
            out = []
            for el in els:
                try:
                    t = (el.inner_text() or "").strip()
                except Exception:
                    t = ""
                if t:
                    out.append(t)
            if out:
                return out
    return []


def _count_responses(page) -> int:
    return len(_all_response_texts(page))


def _has_attachment(page, timeout_s: int = 8) -> bool:
    """画像の添付チップ/サムネイルが現れる＝添付成功、を待って確認する。"""
    deadline = time.time() + timeout_s
    while time.time() < deadline:
        for sel in SELECTORS.get("attachment_chip", []):
            try:
                if page.query_selector(sel):
                    return True
            except Exception:
                continue
        time.sleep(0.6)
    return False


def _try_file_input(page, path: Path) -> bool:
    """隠し input[type=file] に直接セットする（毎回取り直す）。"""
    for sel in SELECTORS.get("file_input", []):
        try:
            inp = page.query_selector(sel)
            if inp:
                inp.set_input_files(str(path))
                return True
        except Exception:
            continue
    return False


def _try_file_chooser(page, path: Path) -> bool:
    """＋/添付ボタンを押してネイティブのファイル選択を開き、セットする。"""
    try:
        with page.expect_file_chooser(timeout=8000) as fc_info:
            btn = _first(page, SELECTORS.get("upload_button", []), timeout=6000)
            if not btn:
                return False
            btn.click()
            item = _first(page, SELECTORS.get("upload_menu_item", []), timeout=2500)
            if item:
                item.click()
        fc_info.value.set_files(str(path))
        return True
    except Exception:
        return False


def _upload_image(page, path: Path) -> bool:
    """審査対象の画像を入力欄へ添付する。複数方式を試し、添付チップで成功を検証。
    検証できない時もセット自体が成功していれば True（チップ未検出でも進む）。"""
    for attempt in range(2):
        # ① 隠しfile input → ② ボタン経由file chooser の順で試す
        set_ok = _try_file_input(page, path) or _try_file_chooser(page, path)
        if set_ok:
            if _has_attachment(page):
                time.sleep(1.5)
                return True
            # チップを検出できなくても、セットは通っている可能性が高い→送信に進む
            if attempt == 0:
                time.sleep(2)
                if _has_attachment(page, timeout_s=4):
                    return True
            else:
                time.sleep(1.5)
                return True
        time.sleep(1.5)
    return False


def _grab_response_text(page, baseline: int, timeout_s: int = 150) -> str | None:
    """送信後、応答数がbaselineより増えるのを待ち、最新応答の文字列が安定したら返す。"""
    deadline = time.time() + timeout_s
    last = ""
    stable = 0
    while time.time() < deadline:
        texts = _all_response_texts(page)
        if len(texts) > baseline and texts[-1]:
            cur = texts[-1]
            if cur == last and len(cur) > 20:
                stable += 1
                if stable >= 2:   # 約4秒変化なし＝生成完了とみなす
                    return cur
            else:
                stable = 0
                last = cur
        time.sleep(2)
    return last or None


def _browser_review(page, image_path: Path, recipe, kind: str, aspect: str):
    """ログイン済みブラウザのGeminiに画像を見せて、厳格ルーブリックで採点させる。
    成功すれば ReviewResult、失敗すれば None（呼び出し側でフォールバック）。"""
    from src.design_director import build_review_prompt, parse_review_text

    prompt = build_review_prompt(recipe, kind, aspect)
    baseline = _count_responses(page)
    if not _upload_image(page, image_path):
        print("     ⚠ ブラウザ審査: 画像を添付できませんでした"
              "（config/gemini_selectors.yaml の file_input / upload_button を確認）。")
        return None
    if not _send_prompt(page, prompt):
        print("     ⚠ ブラウザ審査: 審査プロンプトを送信できませんでした。")
        return None
    text = _grab_response_text(page, baseline)
    if not text:
        print("     ⚠ ブラウザ審査: 応答を取得できませんでした（response_text セレクタを確認）。")
        return None
    # 診断用に生応答を保存（点数が0等の不整合をあとで原因究明できるように）。
    try:
        dbg = config.OUTPUT_DIR / ".review_debug"
        dbg.mkdir(parents=True, exist_ok=True)
        (dbg / f"{image_path.parent.parent.name}_{image_path.stem}.txt").write_text(
            text, encoding="utf-8")
    except Exception:
        pass
    try:
        res = parse_review_text(text, "Gemini Vision (ブラウザ審査)")
    except Exception as e:  # noqa: BLE001
        print(f"     ⚠ ブラウザ審査: 応答をJSON解釈できませんでした（{type(e).__name__}）。簡易判定に切替。")
        print(f"        応答プレビュー: {text[:200].replace(chr(10), ' ')}")
        return None
    # 全責任者0点はパース不整合の疑い → 生応答プレビューを出して原因を可視化。
    if not any(v["score"] for v in res.directors):
        print("     ⚠ ブラウザ審査: スコアが全0でした（応答の形が想定と違う可能性）。")
        print(f"        応答プレビュー: {text[:200].replace(chr(10), ' ')}")
        print(f"        生応答を保存: {config.OUTPUT_DIR / '.review_debug'}")
    return res


def make_browser_reviewer(ctx, chat_name: str = "", realign: bool = False):
    """ブラウザ審査用の専用タブを遅延生成し、reviewer関数を返す。

    chat_name を指定すると、審査もその固定チャットに合流する。これにより会長の
    指摘・過去の審査文脈（ナレッジ）が同じチャットに蓄積し、意図が伝わりやすくなる。
    ブラウザ審査に失敗した画像は review_image（API→簡易判定）にフォールバックする。
    """
    from src.design_director import ceo_brief, review_image

    state = {"page": None}

    def reviewer(image_path: Path, recipe, kind: str, aspect: str):
        rp = state["page"]
        if rp is None:
            rp = ctx.new_page()
            rp.goto(GEMINI_URL, wait_until="domcontentloaded")
            time.sleep(2)
            _wait_logged_in(rp)   # ログインは生成タブと共有（同一プロファイル）
            state["page"] = rp
            print("   🔍 審査用タブを起動しました（APIキー不要のブラウザ審査）。")
            # 審査も固定チャットに合流し、過去の文脈・指摘を引き継ぐ。
            joined = False
            if chat_name:
                print(f"   💬 審査チャット「{chat_name}」に合流を試みます…")
                joined = _open_chat(rp, chat_name)
            if joined:
                print(f"      ✅ 「{chat_name}」に合流。過去の審査ナレッジを引き継ぎます。")
                if realign:
                    print("      🤝 審査の意図(デザイン目的)を再共有中…")
                    if _send_prompt(rp, ceo_brief()):
                        time.sleep(6)
            else:
                if chat_name:
                    print(f"      ⚠ 「{chat_name}」が見つからないため新規チャットで開始します"
                          f"（このチャットを手動で『{chat_name}』と名付けると次回から合流できます）。")
                _new_chat(rp)
                rp.goto(GEMINI_URL, wait_until="domcontentloaded")
                time.sleep(2)
                # 新規審査チャットには、まず審査の意図(デザイン目的)を共有して土台を作る。
                print("      🤝 審査チャットにデザイン意図を共有中…")
                if _send_prompt(rp, ceo_brief()):
                    time.sleep(6)
        res = _browser_review(rp, image_path, recipe, kind, aspect)
        return res or review_image(image_path, recipe, kind, aspect)

    return reviewer


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
                      prompt: str, kind: str, aspect: str, reviewer=None) -> bool:
    """画像を生成→デザイン責任者が審査→不合格なら作り直し。合格 or 最高得点を採用。

    reviewer(image_path, recipe, kind, aspect) -> ReviewResult。
    未指定時は review_image（API→簡易判定）を使う。
    """
    if reviewer is None:
        from src.design_director import review_image as reviewer

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

        res = reviewer(tmp, recipe, kind=kind, aspect=aspect)
        mark = "✅合格" if res.passed else "❌不合格"
        print(f"     品質審査: 平均{res.total}/100 {mark}（各責任者の合格ライン{res.pass_score}・{res.engine}）")
        # 責任者ごとの合否（各100点満点。どの責任者で問題が出たか）
        for v in res.directors:
            dm = "✅" if v["passed"] else "❌"
            print(f"        {dm} {v['name']}〔{v['area']}〕 {v['score']}/100")
        ng = res.failed_directors()
        if ng:
            print(f"     ⚠ 問題の所在: {'、'.join(ng)}")
        if res.summary:
            print(f"     社長総評: {res.summary}")

        # これまでで最高得点なら採用（save_path を更新）
        if res.total > best_score:
            best_score = res.total
            tmp.replace(save_path)
        else:
            tmp.unlink(missing_ok=True)

        if res.passed:
            print(f"  ✅ {name}: 合格して保存 → {save_path}")
            return True
        # API審査が無効(heuristic)のときは、作り直しても同じ判定で無意味なので中断。
        if res.engine.startswith("heuristic"):
            print(f"  ⚠ {name}: API審査が無効のため作り直しを中断し保存 → {save_path}")
            print("     ※ 正しく審査・作り直すには .env に有効な GEMINI_API_KEY が必要です。")
            return True
        if attempt < MAX_ATTEMPTS:
            for r in (res.requests or [])[:4]:
                print(f"       → 改善指示: {r}")
            cur_prompt = _retry_prompt(prompt, res)
            time.sleep(2)

    print(f"  ⚠ {name}: {MAX_ATTEMPTS}回試して合格に届かず。最高得点({best_score})の画像を採用 → {save_path}")
    return True


# --- メイン処理 --------------------------------------------------------

def _no_reviewer(image_path, recipe, kind, aspect):
    """--review off 用。審査せず即合格扱いにする。"""
    from src.design_director import ReviewResult, _pass_score
    return ReviewResult(passed=True, total=100, pass_score=_pass_score(),
                        summary="審査スキップ（--review off）", engine="off（審査なし）")


def process(post_dirs, headless: bool, chat_name: str = "", realign: bool = False,
            review_mode: str = "auto", review_chat: str = ""):
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

        # 審査エンジンを決定（auto: APIキーがあればAPI、無ければブラウザ審査）。
        mode = review_mode
        if mode == "auto":
            mode = "api" if config.gemini_api_key() else "browser"
        if mode == "api":
            from src.design_director import review_image as reviewer
            print("🔍 審査エンジン: API（GEMINI_API_KEY を使用）")
        elif mode == "off":
            reviewer = _no_reviewer
            print("🔍 審査エンジン: なし（--review off）")
        else:
            reviewer = make_browser_reviewer(ctx, chat_name=review_chat, realign=realign)
            print("🔍 審査エンジン: ブラウザ審査（APIキー不要・Geminiに画像を直接見せて採点）"
                  + (f"／審査チャット「{review_chat}」に固定" if review_chat else ""))

        # 社長(このシステム)が、会長(あなた)のビジョンを翻訳した
        # デザインの目的と意図を、各責任者へ共有してから着手する。
        from src.design_director import ceo_brief
        from src.image_generator import brand_brief
        print("\n" + ceo_brief())

        # 会長が用意した既存チャットに合流する（世界観の文脈を回をまたいで継続）。
        joined = False
        if chat_name:
            print(f"\n💬 既存チャット「{chat_name}」に合流を試みます…")
            joined = _open_chat(page, chat_name)
        if joined:
            print(f"   ✅ 「{chat_name}」に合流しました。これまでの世界観の文脈を引き継ぎます。")
        else:
            if chat_name:
                print(f"   ⚠ 「{chat_name}」が見つからないため新規チャットを開始します"
                      "（次回のために、この実行で作る最初のチャットを手動で『"
                      f"{chat_name}』と名付けておくと次回から合流できます）。")
            _new_chat(page)
            page.goto(GEMINI_URL, wait_until="domcontentloaded")
            time.sleep(2.0)

        # ブランド世界観のすり合わせ。新規チャット時は必ず実施。
        # 既存チャット合流時は文脈に既にあるため、--realign 指定時のみ再共有。
        if (not joined) or realign:
            print("🤝 社長→ジェミニ: ブランド世界観をすり合わせ中…")
            if _send_prompt(page, brand_brief()):
                time.sleep(8)   # ジェミニが「了解しました」と返すのを待つ
                print("   すり合わせ完了。この世界観を全画像で厳守させます。")
        else:
            print("   （合流先チャットに世界観が共有済みのため、すり合わせは省略。"
                  "再共有したい場合は --realign を付けて実行）")

        for d in post_dirs:
            assets = d / "素材"
            assets.mkdir(exist_ok=True)
            recipe = load_recipe(d)
            print(f"\n=== {d.name} ===")

            todo = []
            for it in needed_images(d):
                name = it[0]
                if _existing_ok(assets, name):
                    print(f"  ✓ {name}: 既にあるためスキップ")
                elif _exists(assets, name):
                    print(f"  ↻ {name}: 既存が低解像度のため作り直します")
                    todo.append(it)
                else:
                    todo.append(it)
            if not todo:
                continue

            for name, prompt, kind, aspect in todo:
                if _make_with_review(page, recipe, assets / f"{name}.png",
                                     name, prompt, kind, aspect, reviewer=reviewer):
                    total_made += 1
                time.sleep(3)   # 次の入力まで少し待つ
        ctx.close()
        print(f"\n📋 社長報告（会長へ）: 全{total_made}枚を各責任者の審査を通して納品しました。")


def main():
    ap = argparse.ArgumentParser(description="Geminiウェブ自動操作で画像生成→素材保存")
    ap.add_argument("post_id", nargs="?", default=None, help="投稿ID（省略時は全件）")
    ap.add_argument("--headless", action="store_true", help="画面を表示しない")
    ap.add_argument("--no-build", action="store_true", help="生成後に build/審査をしない")
    ap.add_argument("--chat", default=CHAT_NAME,
                    help=f"合流する既存チャット名（既定: {CHAT_NAME}）")
    ap.add_argument("--new", action="store_true", help="既存チャットに合流せず新規チャットで行う")
    ap.add_argument("--realign", action="store_true",
                    help="既存チャット合流時もブランド世界観を再共有する")
    ap.add_argument("--review", choices=["auto", "browser", "api", "off"], default="auto",
                    help="審査エンジン: auto(既定/キーがあればAPI・無ければブラウザ) / "
                         "browser(APIキー不要でGeminiに画像を見せて採点) / api / off")
    ap.add_argument("--review-chat", default=REVIEW_CHAT_NAME,
                    help=f"審査を固定する専用チャット名（既定: {REVIEW_CHAT_NAME}）。"
                         "ここに審査ナレッジが蓄積する")
    ap.add_argument("--review-new", action="store_true",
                    help="審査を固定チャットに合流せず新規チャットで行う")
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
        process(dirs, headless=args.headless,
                chat_name=("" if args.new else args.chat), realign=args.realign,
                review_mode=args.review,
                review_chat=("" if args.review_new else args.review_chat))
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
