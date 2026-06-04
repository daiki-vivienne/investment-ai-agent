# Investment AI Agent

決算PDFを読み込み、AIで投資家目線の分析レポートをMarkdownとして保存するCLIアプリです。

Ver0.1では、1つのPDFを読み込んでレポートを作成する最小構成にしています。自動売買はまだ実装していません。

## セットアップ手順

1. Python 3.10以上を用意します。

2. このフォルダで仮想環境を作成します。

```powershell
python -m venv .venv
```

3. 仮想環境を有効化します。

```powershell
.venv\Scripts\Activate.ps1
```

4. 必要なライブラリをインストールします。

```powershell
pip install -r requirements.txt
```

## .envの作り方

`.env.example` をコピーして `.env` を作ります。

```powershell
Copy-Item .env.example .env
```

`.env` を開き、`OPENAI_API_KEY` に自分のOpenAI APIキーを設定します。

```env
OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxx
OPENAI_MODEL=gpt-4o-mini
```

APIキーは秘密情報です。GitHubなどに公開しないでください。

## PDFの置き場所

分析したい決算PDFは、以下のフォルダに置くと管理しやすいです。

```text
data/pdfs/
```

例:

```text
data/pdfs/sample_financial_report.pdf
```

## 実行方法

PDFファイルのパスを指定して実行します。

```powershell
python main.py data/pdfs/sample_financial_report.pdf
```

保存先フォルダを変えたい場合は、`--output-dir` を使います。

```powershell
python main.py data/pdfs/sample_financial_report.pdf --output-dir data/reports
```

## 出力されるレポートの場所

初期設定では、Markdownレポートは以下に保存されます。

```text
data/reports/
```

ファイル名には、元PDF名と作成日時が入ります。

```text
sample_financial_report_analysis_20260604_120000.md
```

## 出力される分析項目

このアプリは単なる要約ではなく、投資家目線で以下の項目を出力します。

- 会社概要
- 業績サマリー
- ポジティブ要因
- リスク要因
- 半導体・AI観点の分析
- 今後注目すべき指標
- 初心者向け解説
- 投資メモ
- AIスコア

AIスコアでは、成長性、収益性、財務健全性、将来性を0〜100点で出し、それぞれの理由も説明します。

## 将来拡張できるポイント

- 株価取得: 証券コードを入力し、現在株価や過去チャートを取得する
- ニュース取得: 決算後のニュースや市場反応を取得する
- スコアリング強化: AIスコアだけでなく、財務指標を使ったルールベースの点数も追加する
- Discord通知: 作成したレポートや重要イベントをDiscordへ送る
- 複数PDF対応: フォルダ内のPDFをまとめて分析する
- 分割要約: 長いPDFをページごとに要約してから全体分析する
- 半自動売買/自動売買: 十分に検証してから、別モジュールとして慎重に追加する

## 注意点

このアプリが作る内容は、投資助言ではなく学習・調査用の分析メモです。実際の投資判断は、自分で追加調査をしたうえで行ってください。
