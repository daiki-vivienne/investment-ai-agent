# このファイルの役割:
# J-Quantsの期間整合性チェック結果を、Markdownレポートに差し込める文章へ変換します。

from src.jquants_client import JQuantsPeriodCheckResult, NOT_ACQUIRED
from src.valuation_analyzer import PerAnalysisResult


# この関数の役割:
# 値をMarkdown表に安全に表示できる文字列へ変換します。
def format_markdown_value(value: object) -> str:
    if value is None:
        return NOT_ACQUIRED

    return str(value).replace("\n", " ").replace("|", "/")


# この関数の役割:
# J-Quantsのチェック結果から、AIに渡す短い文脈を作ります。
# なぜ必要か:
# AIが期間不一致の参考データを正式データのように扱わないよう、明確な指示を一緒に渡すためです。
def build_api_context_for_ai(period_check_result: JQuantsPeriodCheckResult | None) -> str:
    if period_check_result is None:
        return (
            "正式データ取得状態: 未取得。\n"
            "J-Quants正式データは未取得です。"
            "売上、営業利益、純利益、EPSなどの定量評価は断定せず、PDF由来の数値も正式データとして使わないでください。"
        )

    if not period_check_result.is_period_matched:
        return (
            "正式データ取得状態: 未取得。\n"
            f"ユーザー指定期間: {period_check_result.requested_period_type} / "
            f"{period_check_result.requested_fiscal_year_end}。"
            "この期間に一致するJ-Quants statementは未取得です。"
            "期間が一致しない参考データは、分析やPER計算に使わないでください。"
            "業績サマリーでは売上、営業利益、純利益、EPSを未取得と表示してください。"
            "PDF由来の数値や『過去最高』『大幅増加』『改善』などの定量表現は、別枠の参考情報としてだけ扱ってください。"
        )

    lines = [
        "正式データ取得状態: 取得済み。",
        f"ユーザー指定期間: {period_check_result.requested_period_type} / {period_check_result.requested_fiscal_year_end}。",
        "J-Quantsで同じ期間のstatementを取得できました。以下のみ正式データ候補として扱えます。",
        "",
        "| 項目 | 値 | 単位 | 元フィールド | 状態 |",
        "| --- | --- | --- | --- | --- |",
    ]

    for item_key, item in period_check_result.formal_data_items.items():
        lines.append(f"| {item_key} | {item.value} | {item.unit} | {item.raw_field_name} | {item.status} |")

    return "\n".join(lines)


# この関数の役割:
# J-Quantsの正式データから、AIに任せず機械的に業績サマリーを作ります。
# なぜ必要か:
# AIに売上・利益・EPSを書かせると、PDF由来の数値や別定義の数値と混ざる可能性があるためです。
def build_formal_performance_summary_markdown(period_check_result: JQuantsPeriodCheckResult | None) -> str:
    if period_check_result is None or not period_check_result.is_period_matched:
        return """
## API正式業績サマリー

| 項目 | 値 | 単位 | 期間末 | データ元 | 状態 |
| --- | --- | --- | --- | --- | --- |
| 売上 | 未取得 | - | - | J-Quants | 未取得 |
| 営業利益 | 未取得 | - | - | J-Quants | 未取得 |
| 純利益 | 未取得 | - | - | J-Quants | 未取得 |
| EPS | 未取得 | - | - | J-Quants | 未取得 |
| 前年同期比 | 未取得 | - | - | J-Quants | 未取得 |

ユーザー指定期間と一致するJ-Quants正式データが未取得のため、業績の定量判断は行いません。
""".strip()

    item_labels = {
        "sales": "売上",
        "operating_profit": "営業利益",
        "net_income": "純利益",
        "eps": "EPS",
    }
    lines = [
        "## API正式業績サマリー",
        "",
        "| 項目 | 値 | 単位 | 期間末 | データ元 | 元フィールド | 状態 |",
        "| --- | --- | --- | --- | --- | --- | --- |",
    ]

    for item_key, label in item_labels.items():
        item = period_check_result.formal_data_items[item_key]
        lines.append(
            "| "
            f"{label} | "
            f"{format_markdown_value(item.value)} | "
            f"{format_markdown_value(item.unit)} | "
            f"{format_markdown_value(item.period_end)} | "
            f"{format_markdown_value(item.source)} | "
            f"{format_markdown_value(item.raw_field_name)} | "
            f"{format_markdown_value(item.status)} |"
        )

    lines.append("| 前年同期比 | 未取得 | - | - | J-Quants | - | 未取得 |")
    lines.append("")
    lines.append("このセクションはJ-Quants正式データから機械的に生成しています。PDF由来の数値は混ぜていません。")

    return "\n".join(lines)


# この関数の役割:
# PER分析結果をMarkdownセクションに変換します。
def build_per_analysis_markdown(per_analysis_result: PerAnalysisResult | None) -> str:
    if per_analysis_result is None:
        return """
## PER分析

PER分析は未実行です。

`--stock-code` と、期間一致したJ-Quants正式EPSがある場合のみPERを計算します。
""".strip()

    return f"""
## PER分析

| 項目 | 内容 |
| --- | --- |
| PER種別 | {format_markdown_value(per_analysis_result.per_type)} |
| 現在株価 | {format_markdown_value(per_analysis_result.current_price)} |
| EPS | {format_markdown_value(per_analysis_result.eps)} |
| EPS対象期間 | {format_markdown_value(per_analysis_result.eps_period_type)} |
| 現在株価ベースの実績PER | {format_markdown_value(per_analysis_result.per)} |
| 状態 | {format_markdown_value(per_analysis_result.status)} |
| 株価データ元 | {format_markdown_value(per_analysis_result.price_source)} |
| EPSデータ元 | {format_markdown_value(per_analysis_result.eps_source)} |
| 時点 | {format_markdown_value(per_analysis_result.as_of_date)} |
| 注意 | 株価は現在時点、EPSは指定決算期の実績値です。 |
| 補足 | {format_markdown_value(per_analysis_result.note)} |
""".strip()


# この関数の役割:
# Markdownレポート冒頭に追加する「期間整合性チェック」セクションを作ります。
def build_period_consistency_markdown(period_check_result: JQuantsPeriodCheckResult | None) -> str:
    if period_check_result is None:
        return """
## 期間整合性チェック

J-Quants APIデータは未取得です。

CLIで `--period-type`、`--fiscal-year-end`、`--stock-code` を指定すると、ユーザー指定の決算期とAPIデータの期間一致を確認できます。

期間が一致しないAPIデータやPDF由来の数値は、正式データとして分析やPER計算に使いません。
""".strip()

    matched_text = "一致" if period_check_result.is_period_matched else "不一致"
    warning_text = period_check_result.warning_message or "期間は一致しています。"
    subscription_note = period_check_result.subscription_note or "無料プラン取得可能期間外を示すAPI応答は確認されていません。"

    lines = [
        "## 期間整合性チェック",
        "",
        "| 項目 | 内容 |",
        "| --- | --- |",
        f"| ユーザー指定 period_type | {format_markdown_value(period_check_result.requested_period_type)} |",
        f"| ユーザー指定 fiscal_year_end | {format_markdown_value(period_check_result.requested_fiscal_year_end)} |",
        f"| J-Quants期間一致 | {matched_text} |",
        f"| WARNING | {format_markdown_value(warning_text)} |",
        f"| 無料プラン/契約範囲メモ | {format_markdown_value(subscription_note)} |",
        "",
        "### 正式データ候補",
        "",
        "ユーザー指定の決算期と一致した場合のみ、以下を正式データ候補として扱います。",
        "",
        "| 項目 | 値 | 単位 | 期間末 | データ元 | 元フィールド | 状態 | 補足 |",
        "| --- | --- | --- | --- | --- | --- | --- | --- |",
    ]

    for item_key, item in period_check_result.formal_data_items.items():
        lines.append(
            "| "
            f"{format_markdown_value(item_key)} | "
            f"{format_markdown_value(item.value)} | "
            f"{format_markdown_value(item.unit)} | "
            f"{format_markdown_value(item.period_end)} | "
            f"{format_markdown_value(item.source)} | "
            f"{format_markdown_value(item.raw_field_name)} | "
            f"{format_markdown_value(item.status)} | "
            f"{format_markdown_value(item.note)} |"
        )

    lines.extend(
        [
            "",
            "### 参考データ一覧",
            "",
            "以下はJ-Quantsから取得できたstatement一覧です。ユーザー指定期間と一致しないデータは参考情報であり、分析やPER計算には使いません。",
            "",
            "| disclosed_date | document_type | current_period_type | current_period_end | current_fiscal_year_end | sales | operating_profit | net_income | eps |",
            "| --- | --- | --- | --- | --- | --- | --- | --- | --- |",
        ]
    )

    for statement in period_check_result.statements:
        lines.append(
            "| "
            f"{format_markdown_value(statement.disclosed_date)} | "
            f"{format_markdown_value(statement.document_type)} | "
            f"{format_markdown_value(statement.current_period_type)} | "
            f"{format_markdown_value(statement.current_period_end)} | "
            f"{format_markdown_value(statement.current_fiscal_year_end)} | "
            f"{format_markdown_value(statement.sales)} | "
            f"{format_markdown_value(statement.operating_profit)} | "
            f"{format_markdown_value(statement.net_income)} | "
            f"{format_markdown_value(statement.eps)} |"
        )

    return "\n".join(lines)
