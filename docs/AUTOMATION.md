# モード②: ブラウザ自動化でGeminiに画像を作らせる

`auto_gemini.py` が、あなたのPCでGeminiウェブ版（gemini.google.com）を
自動操作して画像を生成し、各投稿の **「素材」フォルダへ自動保存**します。
そのまま合成（`--build`）と品質審査まで自動で続けます。

> ⚠️ **必ずお読みください**
> - これは **あなたのPCで実行**します（クラウド側では動きません）。
> - 消費者向けGeminiの自動操作は **Google利用規約に抵触する恐れ**があり、
>   アカウント制限のリスクがあります。**自己責任**でご利用ください。
> - 安定・安全に全自動化したいなら **API課金（モードA）** を推奨します
>   （Chrome不要・規約クリーン・1投稿45〜135円）。

## 準備（初回のみ）

```bash
pip install -r requirements-automation.txt
playwright install chromium
```

## 使い方

```bash
# 1) まず投稿（レシピ＋枠）を作る
python run.py

# 2) Geminiで画像を自動生成して素材フォルダへ保存
python auto_gemini.py                 # 全投稿の不足画像を生成
python auto_gemini.py 2026-06-15_01   # 投稿を指定
```

- 初回はブラウザが開きます。**Geminiにログイン**して、ターミナルで Enter を押してください。
  ログイン状態は `.gemini_profile/`（gitignore済み）に保存され、次回以降は自動です。
- 生成後、自動で `python run.py --build`（合成＋品質審査）まで実行します。
- 既に素材がある画像はスキップします。

## うまく動かないとき（UI変更でセレクタがずれた場合）

GeminiのWeb UIは頻繁に変わります。入力欄や画像が見つからない場合は、
ブラウザの「検証(F12)」で要素を調べ、**`config/gemini_selectors.yaml`** の
該当セレクタを書き換えてください（コードの変更は不要）。

- `input_box` … プロンプト入力欄
- `send_button` … 送信ボタン
- `response_image` … 生成された画像
- `logged_in_marker` … ログイン済み判定に使う要素

## 画像が自動取得できなかったとき

スクリプトが画像を取れなかった場合は、その場で手動ダウンロードして
指定パス（例: `output/<投稿>/素材/hero.png`）に置けばOKです。
その後 `python run.py --build` で合成・審査されます。
