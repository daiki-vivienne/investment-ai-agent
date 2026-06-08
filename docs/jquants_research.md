# J-Quants Research

このドキュメントは、J-Quants APIを今後の正式データソース候補にできるかを調査するためのメモです。

対象銘柄はキオクシア `285A` です。

## 目的

yfinanceでは株価や財務データを取得できましたが、データ時点、会計基準、単位、更新タイミングの確認が必要でした。

J-Quants APIはJPX系のデータサービスであり、日本株の株価や財務情報を取得する正式データソース候補として調査します。

## 今回調べる項目

- 売上
- 営業利益
- 純利益
- EPS

## 認証

J-Quants APIは、V2でAPIキー認証へ移行しています。

そのため、この調査では `.env` の `JQUANTS_API_KEY` を優先して使います。

`.env` に以下を設定してください。

```env
JQUANTS_API_KEY=your_api_key_here
```

古いrefresh token方式を使う場合は `JQUANTS_REFRESH_TOKEN` も読み込めるようにしていますが、`/v1/token/auth_refresh` が `HTTP 410 Gone` になる場合は、V1エンドポイントが利用できない可能性が高いためV2 APIキー方式へ移行してください。

## 調査用スクリプト

既存システムには統合せず、調査用スクリプトとして実行します。

```powershell
python src/jquants_research_sample.py
```

対象PDFと同じ期間のstatementを選びたい場合は、`--period-type` と `--fiscal-year-end` を指定します。

```powershell
python src/jquants_research_sample.py 285A --period-type FY --fiscal-year-end 2026-03-31
```

3Q資料と比較したい場合は、以下のように指定します。

```powershell
python src/jquants_research_sample.py 285A --period-type 3Q --fiscal-year-end 2026-03-31
```

## J-Quants API候補

| 用途 | エンドポイント | 方針 |
| --- | --- | --- |
| APIキー認証 | `x-api-key` ヘッダー | V2 APIで優先して利用 |
| ID token取得 | `/v1/token/auth_refresh` | 旧方式。410 Goneになる場合はV2へ移行 |
| 日次株価 | `/prices/daily_quotes` | 将来的な現在株価・過去株価の正式候補 |
| 財務サマリー | `/v2/fins/summary` | 売上、営業利益、純利益、EPSの取得候補 |
| 財務情報 | `/v1/fins/statements` | 旧方式の取得候補 |
| 財務諸表詳細 | `/fins/fs_details` | BS/PL/CFの詳細取得候補 |

## yfinanceとの比較方針

| 項目 | J-Quants | yfinance | 確認したいこと |
| --- | --- | --- | --- |
| 売上 | `/v2/fins/summary` 候補 | `financials` / `totalRevenue` | 決算期、単位、会計基準が一致するか |
| 営業利益 | `/v2/fins/summary` 候補 | `financials.Operating Income` | IFRS/Non-GAAPの違い |
| 純利益 | `/v2/fins/summary` 候補 | `financials.Net Income` | 親会社帰属利益かどうか |
| EPS | `/v2/fins/summary` 候補 | `trailingEps` | TTM/通期/Non-GAAPの違い |

## 2026-06-08 実行メモ

旧refresh token方式で `/v1/token/auth_refresh` を実行したところ、`HTTP 410 Gone` が返りました。

レスポンスには以下の内容が含まれていました。

```json
{
  "message": "J-QuantsはV2に移行しました。",
  "migration_url": "https://jpx-jquants.com/ja/spec/migration-v1-v2"
}
```

この結果から、少なくとも今回の環境ではV1の認証エンドポイントを前提にした調査は継続できません。次回は `JQUANTS_API_KEY` を `.env` に設定し、V2 APIの `/v2/fins/summary` で再実行します。

## 2026-06-08 V2実行結果メモ

`JQUANTS_API_KEY` を使ったV2 APIでは、キオクシア `285A` の財務サマリーを取得できました。

取得結果から、V2では `DiscDate`、`DocType`、`CurFYEn`、`CurPerEn`、`Sales`、`EPS` などの短縮フィールドが使われていることが分かりました。

初回実装ではV1系のフィールド名を中心に見ていたため、営業利益と純利益が未取得になりました。今後はV2の短縮フィールド名も候補に入れて確認します。

| 項目 | J-Quants値 | J-Quants元フィールド | 状態 | yfinance値 | 注意点 |
| --- | --- | --- | --- | --- | --- |
| 売上 | 1,359,366,000,000円 | Sales | 取得済み | 2,337,627,963,392 | 時点や会計期間が一致しているか確認が必要 |
| 営業利益 | 未取得 | OperatingProfit/OperatingIncome | 未取得 | 451,748,000,000 | V2短縮フィールド `OP` の確認が必要 |
| 純利益 | 未取得 | Profit/ProfitAttributableToOwnersOfParent/NetIncome | 未取得 | 272,315,000,000 | V2短縮フィールド `NP` の確認が必要 |
| EPS | 485.94円 | EPS | 取得済み | 1,008.01 | J-Quantsとyfinanceで定義や対象期間が異なる可能性がある |

この差分から、J-Quantsは正式データソース候補として有力ですが、yfinanceと値が一致しない項目は「どちらが正しいか」ではなく、まず対象期間、会計基準、TTM/通期、連結/単体、Non-GAAP/GAAPの違いを確認する必要があります。

## 2026-06-08 V2フィールド追加確認

V2の短縮フィールド `OP` と `NP` を候補に追加したところ、売上、営業利益、純利益、EPSをすべて取得できました。

今回の最新レコードは `DocType` が `3QFinancialStatements_Consolidated_IFRS` でした。そのため、取得値は通期ではなく3Q累計の可能性が高く、通期のyfinance値と単純比較してはいけません。

| 項目 | J-Quants値 | 元フィールド | 状態 | yfinance値 | 解釈 |
| --- | --- | --- | --- | --- | --- |
| 売上 | 1,334,776,000,000円 | Sales | 取得済み | 2,337,627,963,392 | J-Quantsは3Q累計、yfinanceはTTMまたは通期の可能性 |
| 営業利益 | 273,574,000,000円 | OP | 取得済み | 451,748,000,000 | J-Quantsは3Q累計、yfinanceは通期系の可能性 |
| 純利益 | 146,756,000,000円 | NP | 取得済み | 272,315,000,000 | `NP` の定義確認が必要 |
| EPS | 271.67円 | EPS | 取得済み | 1,008.01 | J-Quantsは対象決算期間、yfinanceはtrailing EPSの可能性 |

次の実装方針として、J-Quants由来データには必ず `DocType`、`CurPerType`、`CurPerEn`、`CurFYEn`、`DiscDate` を付けます。これにより、3Q累計と通期を混同しないようにします。

## 期間指定によるstatement選択

財務データは「取得できたか」だけでは不十分です。

投資分析では、PDFとAPIデータの対象期間が一致している必要があります。たとえば、PDFが2026年3月期通期なのに、J-Quants側で2026年3月期3Q累計を使うと、売上・利益・EPSの比較がズレます。

そのため、調査スクリプトでは以下を必ず一覧表示します。

- disclosed_date
- document_type
- current_period_type
- current_period_end
- current_fiscal_year_end
- sales
- operating_profit
- net_income
- eps

さらに、`--period-type` と `--fiscal-year-end` を指定すると、条件に一致するstatementだけを選択して主要4項目を表示します。

指定条件に一致するstatementがない場合、財務4項目は「未取得」とし、PDFと同じ期間では比較できないことをWARNINGで表示します。

## 利用しているJ-Quants APIの種類

現在の調査スクリプトは、J-Quants V2の `https://api.jquants.com/v2/fins/summary` を使っています。

これは、決算短信サマリーのような主要財務数値を取得するFinancial Data API側の取得処理です。

一方、Financial Statement Data(BS/PL/CF) APIは、BS、PL、CFの明細項目を取得するためのAPIです。公式ドキュメントでは `/fins/fs_details` として説明されています。現在の調査スクリプトでは、まだこのBS/PL/CF詳細APIは使っていません。

### 285Aの2026年3月期FYが取得できない理由の仮説

2026-06-08時点の実行結果では、J-Quantsから取得できた最新statementは以下でした。

- disclosed_date: 2026-02-12
- current_period_type: 3Q
- current_period_end: 2025-12-31
- current_fiscal_year_end: 2026-03-31

一方、キオクシアの2026年3月期通期PDFは2026年5月開示の資料です。

そのため、現時点で `FY / 2026-03-31` が取得できない理由としては、無料プラン等の配信遅延またはプラン制限の可能性が最も高いです。

| 可能性 | 評価 | 理由 |
| --- | --- | --- |
| APIエンドポイントの違い | 中 | 現在はFinancial Data側を使用。売上、営業利益、純利益、EPSは取れているため、主要4項目だけならエンドポイント違いが主因とは言いにくい。ただしBS/PL/CF明細まで確認するなら `/fins/fs_details` の調査が必要。 |
| 取得条件の指定ミス | 低 | statements一覧に `FY / 2025-03-31` と `3Q / 2026-03-31` は出ているため、コード・銘柄・期間フィルタ自体は動いている。 |
| 無料プランの制限 | 高 | 無料プランではデータ配信が遅延する可能性がある。2026年5月開示の通期データが2026-06-08時点で未取得なのは、この説明と整合する。 |
| J-Quants側にまだデータがない | 中 | 有料プランでも未取得ならこの可能性が上がる。ただし現在の結果だけでは、J-Quants全体に未収録なのか、利用プラン上まだ見えていないのかは切り分けできない。 |

次の調査としては、同じ銘柄・同じ条件で有料プランまたは配信遅延がない環境で再実行するか、`/fins/fs_details` も試してFY開示日のBS/PL/CF詳細が取得できるか確認します。

## Ver3.0完成時点の整理

Ver3.0では、J-Quantsの最新FYを無料プランで必ず取得するところまではスコープにしません。

代わりに、以下を完成条件とします。

- yfinanceで取得できる項目と注意点を整理した
- J-Quants V2 `/v2/fins/summary` で285Aの財務サマリー取得に成功した
- J-Quants無料プランでは取得可能期間に制限があることを確認した
- ユーザー指定の `period_type` / `fiscal_year_end` でstatementを検索できるようにした
- 指定期間と一致しないAPIデータは、正式分析やPER計算に使わない方針にした

本体CLIでは、以下のように実行します。

```powershell
python main.py data/pdfs/kioxia260515_1.pdf --stock-code 285A --period-type FY --fiscal-year-end 2026-03-31
```

この条件でJ-Quants側に一致するstatementがない場合、レポート上では正式データ候補を「未取得」とし、取得できた3Qなどのデータは参考データ一覧に分けて表示します。

重要なのは、APIから数字が取れたかどうかではなく、PDFとAPIの対象期間が一致しているかです。

また、正式データ候補が未取得の場合、AI本文でもPDF由来の数値を根拠にした定量評価やAIスコア算出は行いません。

PDF上の数値は「PDF上の主な記述」として分け、正式データではなく参考情報として扱います。

## 実行結果記入欄

実行後、以下の表に結果を貼り付けます。

| 項目 | J-Quants値 | 単位 | 時点 | J-Quants元フィールド | 状態 | yfinance値 | 補足 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| sales | 未実行 | - | - | - | 未実行 | - | JQUANTS_API_KEY設定後に確認 |
| operating_profit | 未実行 | - | - | - | 未実行 | - | JQUANTS_API_KEY設定後に確認 |
| net_income | 未実行 | - | - | - | 未実行 | - | JQUANTS_API_KEY設定後に確認 |
| eps | 未実行 | - | - | - | 未実行 | - | JQUANTS_API_KEY設定後に確認 |

## 現時点の判断

J-Quantsは、日本株の正式データソース候補として有力です。

ただし、実際に `285A` の財務データが取得できるか、フィールド名が想定どおりか、無料/有料プランで取得できる範囲は確認が必要です。

## 参考リンク

- [J-Quants ID Token /token/auth_refresh](https://jpx.gitbook.io/j-quants-en/api-reference/idtoken)
- [J-Quants API仕様](https://jpx.gitbook.io/j-quants-ja/api-reference)
- [J-Quants API V2対応のお知らせ](https://www.jpx.co.jp/english/corporate/news/news-releases/6020/20260119.html)
- [J-Quants 株価四本値 /prices/daily_quotes](https://jpx.gitbook.io/j-quants-ja/api-reference/daily_quotes)
- [J-Quants Pro 財務情報 /fins/statements](https://jpx.gitbook.io/j-quants-pro-ja/api-reference/statements)
- [J-Quants Pro 財務諸表 /fins/fs_details](https://jpx.gitbook.io/j-quants-pro/api-reference/statements_details)
