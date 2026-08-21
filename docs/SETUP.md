# セットアップ手順

画像の作り方は2モードあります。

- **モードA（全自動）**: Gemini APIで料理写真も自動生成。請求(支払い)の有効化が必要。
- **モードB（無料・手動画像）**: 料理写真はあなたがGeminiアプリ（Pro契約の範囲・無料）で作り、
  システムが表紙・レシピカードに自動合成。← **現在の設定**

---

## モードB（無料）の使い方

> Geminiアプリの画像生成は、あなたのGoogle AI Pro契約の範囲で使えます（API課金なし）。

1. 投稿を生成: `python run.py`
2. `output/<日付_番号>/画像作成ガイド.txt` を開く
3. 中の【プロンプト】を1つずつ **Geminiアプリ**（gemini.google.com）に貼って画像を作る
4. 保存した画像を、ガイドの指定名（`hero.jpg` / `step_1.jpg`〜`step_6.jpg`）にして
   同じ投稿フォルダの **「素材」フォルダ** に入れる
5. 再合成: `python run.py --build`
   → 表紙・レシピカードが、あなたの画像で完成します

画像が足りない分はダミーのまま合成されるので、後から差し替えもOKです。

---

## モードA（全自動）に切り替える場合

このシステムは **APIキーが無くてもダミー画像でレイアウトを確認できます**。
実際の料理写真をAPIで自動生成するには、請求の有効化が必要です。

## 1. Gemini APIキーを取得（無料）

1. https://aistudio.google.com/apikey にアクセス（Googleアカウントでログイン）
2. **「Create API key」** をクリック
3. 表示されたキー（`AIza...`）をコピー

> これがあなたが行う唯一の必須作業です。あとは全自動。

## 2. キーを設定

```bash
cp .env.example .env
# .env を開いて GEMINI_API_KEY=コピーしたキー を貼り付け
```

## 3. 依存をインストール

```bash
pip install -r requirements.txt
# 日本語フォント（未導入の環境のみ／表紙の明朝に必要）
sudo apt-get install -y fonts-ipafont-gothic fonts-ipafont-mincho
```

## 4. 実行（投稿パッケージ生成）

```bash
python run.py            # 今日の投稿を自動生成
python run.py --count 3  # 3件生成
```

`output/<日付_番号>/` に以下が出力されます：

- `slide_01_cover.jpg` … 表紙（暗背景の料理写真＋金/白タイトル）
- `slide_02_recipe.jpg` … レシピカード（材料・調理時間・費用・難易度・手順01〜06）
- `caption.txt` … 本文（材料・手順の全文＋ハッシュタグ。コピペで完成）
- `README.txt` … TikTokへのアップロード手順
- `post.json` … メタ情報

## 5. TikTokへ投稿

スマホに `output/<該当フォルダ>` を送り、`README.txt` の通り
`slide_01`→`slide_02` の順で選んで `caption.txt` を貼るだけ（1〜2分）。

> 完全な自動アップロード（TikTok Content Posting API）は、TikTok側の
> アプリ審査とアクセストークン取得が必要です。希望があれば次段階として
> 実装できます（`docs/STRATEGY.md` 参照）。

## 料金の目安（Gemini 3 Pro Image / Nano Banana Pro）

- 1投稿につき画像を **7枚生成**（ヒーロー1＋工程6）
- 1K〜2K画像 約 $0.13/枚 → 1投稿あたり約 $0.9、1日2投稿で約 $1.8/日
- コストを抑えたい場合:
  - `.env` の `GEMINI_IMAGE_MODEL` を `gemini-2.5-flash-image-preview` に
  - または Batch API（半額・24時間以内）

## 「AIっぽくて作る気がしない」を避けるコツ

ロールモデルのコメントにもあった通り、写真のリアルさが命です。
本システムの画像プロンプトは「本物の家庭料理に見えるリアルな写真／CGっぽくしない」
を明示しています。さらに寄せたい場合は `src/image_generator.py` の
`hero_image()` のプロンプトを調整してください。
