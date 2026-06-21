# Investment AI Agent

決算PDFとAPI由来データを使い、投資判断材料を整理するMarkdownレポートを保存するCLIアプリです。

Ver6.0では「PDFは定性情報」「J-Quantsは正式財務データ」「yfinanceは参考市場データ」と役割を分けたまま、Discord BotからもMarkdownレポートを生成できる試作版を追加しています。

自動売買はまだ実装していません。

## 設計思想

PDFから売上やEPSを無理に抽出すると、脚注や予想レンジを拾って誤検知するリスクがあります。

そのため、このアプリでは以下のように役割を分けます。

```text
PDF
  ↓
定性情報の抽出とAI要約

API
  ↓
J-Quants: 売上、営業利益、純利益、EPS、FEPS、NxFEPSなどの正式財務データ候補
yfinance: 現在株価、PBR、時価総額などの参考市場データ

Markdown
  ↓
PDF由来 / API由来 / AI要約 を分けて出力
```

PDFから機械的に抽出した売上・利益・EPSは、正式データとして表示しません。PER計算などにも使いません。

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
J-Quantsを使う場合は、`JQUANTS_API_KEY` も設定します。
Discord Botを使う場合は、`DISCORD_BOT_TOKEN` も設定します。

```env
OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxx
OPENAI_MODEL=gpt-4o-mini
JQUANTS_API_KEY=your_jquants_api_key_here
DISCORD_BOT_TOKEN=your_discord_bot_token_here
DISCORD_ALLOWED_CHANNEL_ID=123456789012345678
```

APIキーは秘密情報です。GitHubなどに公開しないでください。
`DISCORD_ALLOWED_CHANNEL_ID` は任意設定です。未設定の場合、Discord Botは従来通りすべてのチャンネルで `!analyze` に反応します。

## 実行方法

PDFファイルだけでも実行できます。

```powershell
python main.py data/pdfs/sample_financial_report.pdf
```

J-Quantsの期間整合性チェックも行う場合は、証券コード、決算期間、会計年度末を指定します。

```powershell
python main.py data/pdfs/kioxia260515_1.pdf --stock-code 285A --period-type FY --fiscal-year-end 2026-03-31
```

`--stock-code` はJ-Quantsの財務データ検索と、yfinanceの株価取得に使います。

yfinanceで別tickerを指定したい場合だけ、`--ticker` を使います。

日本株をyfinanceで取得する場合、内部では自動で `.T` を付けます。

```text
285A → 285A.T
```

保存先フォルダを変えたい場合は、`--output-dir` を使います。

```powershell
python main.py data/pdfs/sample_financial_report.pdf --output-dir data/reports
```

## Discord Botの実行方法

Ver6.0では、ローカルで動かす試作用Discord Botを追加しています。

Discord Botを使う場合は、Discord Developer PortalでBotを作成し、`.env` に `DISCORD_BOT_TOKEN` を設定してください。

特定のテキストチャンネルだけでBotを使いたい場合は、`.env` に `DISCORD_ALLOWED_CHANNEL_ID` を設定します。
チャンネル名ではなく、DiscordのチャンネルIDを指定してください。
未設定の場合は、チャンネル制限なしで動作します。

通常メッセージコマンドを使うため、Bot設定で Message Content Intent が必要になる場合があります。

```powershell
python discord_bot.py
```

Discordでは、PDFを1つ添付して以下のように送信します。

```text
!analyze 285A FY 2025-03-31
```

BotはPDFを `data/discord_uploads/` に一時保存し、`src/report_service.py` の `generate_report()` を呼び出してMarkdownレポートを作成します。

生成されたMarkdownレポートは、既存通り `data/reports/` に保存され、Discordにも添付して返信されます。

一時保存したPDFは、処理後に削除します。

注意点:

- Discordの添付ファイルサイズ上限を超えるPDFは送信できません。
- AI分析、J-Quants、yfinanceへの外部通信があるため、分析には時間がかかる場合があります。
- 今回は1回のコマンドにつきPDF 1つだけ対応します。
- `DISCORD_ALLOWED_CHANNEL_ID` を設定した場合、指定チャンネル以外の `!analyze` は無反応になります。
- スラッシュコマンド、本番常駐、クラウドデプロイ、スケジュール通知はまだ実装していません。

## 出力されるレポート

初期設定では、Markdownレポートは以下に保存されます。

```text
data/reports/
```

レポート内では、情報源を分けて表示します。

- PDF由来の参考情報
- API由来データ
- AI要約
- 投資判断支援セクション

## PDF由来の参考情報

PDF由来セクションでは、PDFを定性情報の確認に使うことを明記します。

売上、営業利益、純利益、EPSなどは誤検知の可能性があるため、PDFから機械抽出して正式データとして表示しません。

## API由来データ

正式財務データはJ-Quantsから取得します。

J-Quantsでは、ユーザーがCLIで指定した `--period-type` と `--fiscal-year-end` に一致するstatementだけを正式データ候補として扱います。

取得対象の例です。

J-Quantsで正式データとして扱う主な項目：
- 売上
- 営業利益
- 純利益
- EPS
- FEPS
- NxFEPS

yfinanceで参考市場データとして取得する主な項目：
- 現在株価
- PBR
- 時価総額

今後API拡張で取得したい項目：
- ROE
- 自己資本比率
- 営業CF
- フリーCF

PERは以下の式で計算します。

```text
直近PER = yfinance由来の現在株価 ÷ 期間一致したJ-Quants EPS
会社予想EPSベースの予想PER = yfinance由来の現在株価 ÷ 期間一致したJ-Quants FEPS
次期予想PER候補 = yfinance由来の現在株価 ÷ 期間一致したJ-Quants NxFEPS
```

J-Quants EPS / FEPS / NxFEPS が未取得、0、赤字の場合、該当するPERは計算せず、理由を補足欄に表示します。

株価は現在時点、EPS / FEPS / NxFEPS は指定決算期に一致したstatement内の値です。
TTM、会社予想、次期予想を混同しないよう、データ元と補足をMarkdown上に表示します。

## yfinanceとJ-Quants API

株価取得処理は [src/market_data_client.py] に分離しています。

現在は、株価、PBR、時価総額などの参考市場データにyfinanceを使っています。

売上、営業利益、純利益、EPS、FEPS、NxFEPSなどの正式財務データ候補はJ-Quantsを使います。

将来的には、株価、PBR、時価総額などの市場データも、J-Quantsや他の正式データソースで検証できる設計にします。

## AI要約

AIはPDFから以下のような定性情報を整理します。

- 会社概要
- 主力事業
- ポジティブ要因
- リスク要因
- 半導体・AI観点の分析
- 今後注目すべき指標
- 初心者向け解説
- 投資メモ

AIには株価、EPS、FEPS、NxFEPS、PER、PBR、時価総額を推測させません。

AIには売上、営業利益、純利益、EPSをPDFから抜き出して断定させません。正式データはAPI由来データだけです。

## Ver4.0 直近PERと予想PER

Ver4.0では、J-Quantsの期間一致したstatementから `EPS`、`FEPS`、`NxFEPS` を取得候補に追加しています。

PER分析では以下を表示します。

- 直近PER: yfinance現在株価 ÷ J-Quants EPS
- 会社予想EPSベースの予想PER: yfinance現在株価 ÷ J-Quants FEPS
- 次期予想PER候補: yfinance現在株価 ÷ J-Quants NxFEPS

`FEPS` と `NxFEPS` はJ-Quantsのフィールド定義に従うため、レポートでは元フィールド名と補足を表示します。

期間不一致の場合や、EPSが未取得、0、赤字の場合はPERを計算せず、理由を補足欄に表示します。

PERが1000倍を超える場合は、異常値の可能性があるためWARNINGを表示します。

## Ver5.0 Discord Bot化に向けた共通サービス化

Ver5.0では、`main.py` に集まっていたレポート生成の中心処理を `src/report_service.py` に切り出しています。

CLIも将来のDiscord Botも、同じ `generate_report()` を呼び出してレポートを作成できる設計です。

```text
CLI
  ↓
src/report_service.py の generate_report()
  ↓
Markdownレポート生成

Discord Bot（将来）
  ↓
src/report_service.py の generate_report()
  ↓
Markdownレポート生成
```

今回のVer5.0ではDiscord Bot本体はまだ実装していません。

Discord用トークンやBot起動処理は追加せず、まずは共通処理の土台だけを作っています。

## Ver6.0 Discord Bot試作

Ver6.0では、DiscordにPDFを添付して `!analyze` コマンドを送ると、BotがMarkdownレポートを返せる試作版を追加しています。

Discord Bot専用の分析処理は作らず、Ver5.0で作った `src/report_service.py` の `generate_report()` を使います。

```text
Discord PDF添付
  ↓
discord_bot.py
  ↓
src/report_service.py の generate_report()
  ↓
MarkdownレポートをDiscordに返信
```

Bot自身のメッセージには反応せず、`!analyze` で始まらない通常メッセージは無視します。

`generate_report()` は時間がかかるため、Discord Bot側では `asyncio.to_thread()` を使ってイベントループを塞がないようにしています。

## Ver3.0 データ取得調査

投資判断支援に必要なデータをどこから取得できるか、調査結果を以下にまとめています。

[docs/data_source_research.md](docs/data_source_research.md)

キオクシア `285A.T` を使ったyfinanceの試作用サンプルは以下で実行できます。

```powershell
python src/yfinance_research_sample.py
```

J-Quants APIの調査結果は以下にまとめています。

[docs/jquants_research.md](docs/jquants_research.md)

J-Quantsの調査用サンプルは以下で実行できます。

J-Quants V2を使う場合は、`.env` に `JQUANTS_API_KEY` を設定してください。

```env
JQUANTS_API_KEY=your_api_key_here
```

```powershell
python src/jquants_research_sample.py
```

## Ver3.0 期間整合性チェック

Ver3.0では、PDFから決算期を推測しません。

ユーザーがCLIで指定した決算期を正として扱い、J-Quants APIから同じ期間のstatementを探します。

```powershell
python main.py data/pdfs/kioxia260515_1.pdf --stock-code 285A --period-type FY --fiscal-year-end 2026-03-31
```

期間が一致した場合のみ、J-Quants由来の売上、営業利益、純利益、EPSを正式データ候補として表示します。

期間が一致しない場合は、APIデータが取れていても「参考データ」として表示し、分析やPER計算には使いません。

PER分析では、yfinanceの現在株価と、ユーザー指定期間に一致したJ-Quants EPS / FEPS / NxFEPS だけを使います。必要なEPSが未取得の場合、該当するPERは計算しません。

表示名は「直近PER」「会社予想EPSベースの予想PER」「次期予想PER候補」と分けます。株価は現在時点、EPSは指定決算期の値であり、同じ日付同士の比較ではないためです。

無料プランや契約プランの取得可能期間外とJ-Quantsが返した場合は、Markdownの「期間整合性チェック」セクションに表示します。

API正式データが未取得の場合、AI本文でも売上・利益・EPSを正式データとして断定せず、AIスコアも点数ではなく「未取得」として扱います。

また、PDF上に「過去最高」「大幅増加」などの表現があっても、API正式データが未取得の場合は、本文の分析根拠には使いません。PDF上の記述は参考情報として分けて表示します。

Ver3.0では、API正式データが未取得の場合、AI本文にPDF内の具体的な数値を転記しません。AIがPDF内の数値対応を読み間違える可能性があるためです。

API正式業績サマリーはAIに書かせず、J-Quants正式データからコードで機械的に生成します。AI本文では売上、営業利益、純利益、EPSを再解釈しません。

さらに、AI本文にPDF由来の定量評価表現が混ざった場合に備えて、出力後の安全フィルタで該当セクションを保守的な固定文へ差し替えます。

### Ver3.0のスコープ

- yfinanceで取得できるデータの調査
- J-Quants V2 `/v2/fins/summary` の調査
- J-Quants無料プランの取得可能期間制限の確認
- ユーザー指定の決算期でAPIデータを検索
- PDFとAPIの期間が一致しない場合は、正式分析に使わない

### なぜ期間一致を必須にするのか

PDFが通期決算なのに、API側が3Q累計のデータだと、売上・利益・EPSの比較がズレます。

投資判断支援ツールでは、数字が取れることよりも「同じ期間の数字か」を確認することが重要です。

## PDF由来の定量表現を断定しない理由

決算PDFには、通期、四半期、Non-GAAP、IFRS、業績予想、注記、前年比など、さまざまな数字が混ざっています。

AIがPDFを読むだけで「営業利益が過去最高」「前年比約2倍」「利益率が改善」と断定すると、どの基準の数字なのか分からず、誤解を招く可能性があります。

そのため、API由来データで未取得の項目については、AI要約で定量評価を断定しません。

PDF内の定量的な記述に触れる場合は、以下のように表現します。

```text
PDF上には業績や財務に関する定量情報が掲載されていますが、正式データとしては扱いません。
```

一方で、以下のようには書きません。

```text
営業利益が過去最高です。
前年比で約2倍です。
利益率が改善しています。
```

業績サマリーでは、API未取得の項目は `API未取得` と表示し、PDF上の記述は別枠の `PDF上の主な記述` に分けます。

## データ取得元候補

将来的には、以下のようなデータ取得元との連携を検討できます。

- 株価データ: yfinance、J-Quants API、Yahoo Finance、Alpha Vantage、証券会社API
- 財務データ: J-Quants API、EDINET、TDnet、企業IR、決算短信、有価証券報告書
- アナリスト目標株価: 証券会社レポート、金融情報端末、公開ニュース
- 市場規模データ: 調査会社レポート、業界団体レポート、企業IR資料
- ニュースデータ: Google News、News API、各種メディア

## 将来の拡張計画

- スラッシュコマンドやクラウド常駐など、Discord Botの運用機能を追加する
- 株価、PBR、時価総額などの市場データをJ-Quantsや他の正式データソースで検証できるようにする
- API由来のBPS、自己資本、発行済株式数を使ってPBRなどを安定計算する
- 市場規模データを取り込み、3年後、5年後、10年後の見通しを比較する
- 同業他社データを取り込み、自社スコアの相対評価を出す
- 十分な検証後に、半自動売買や自動売買の別モジュールを検討する

## 注意点

このアプリが作る内容は、投資助言ではなく学習・調査用の分析メモです。実際の投資判断は、自分で追加調査をしたうえで行ってください。
