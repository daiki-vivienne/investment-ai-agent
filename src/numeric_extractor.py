# このファイルの役割:
# PDF由来の情報を参考情報として整理します。
# 注意:
# PDFから売上・利益・EPSを抽出する処理は誤検知リスクが高いため、正式データや投資指標計算には使いません。

from dataclasses import asdict
import json
import re
import unicodedata

from src.data_models import FinancialMetric, NOT_ACQUIRED, StructuredFinancialData


METRIC_ALIASES = {
    "sales": ["売上収益", "売上高", "売上"],
    "operating_profit": ["営業利益"],
    "net_income": ["親会社の所有者に帰属する当期利益", "親会社株主に帰属する当期純利益", "当期利益", "純利益"],
    "eps": ["基本的1株当たり当期利益", "基本的１株当たり当期利益", "1株当たり", "１株当たり", "EPS"],
}

METRIC_LABELS = {
    "sales": "売上",
    "operating_profit": "営業利益",
    "net_income": "純利益",
    "eps": "EPS",
}


# この関数の役割:
# 全角数字や全角記号を半角に寄せ、正規表現で探しやすい文字列にします。
# なぜ必要か:
# PDFから抽出した文字は、全角数字や見えない空白が混ざることがあり、そのままだと抽出漏れが起きやすいためです。
def normalize_pdf_text(extracted_pdf_text: str) -> str:
    normalized_text = unicodedata.normalize("NFKC", extracted_pdf_text)
    normalized_text = normalized_text.replace("△", "-")
    normalized_text = normalized_text.replace("▲", "-")

    return normalized_text


# この関数の役割:
# 数値文字列からカンマを外してfloatに変換します。
def parse_number(number_text: str) -> float:
    cleaned_number_text = number_text.replace(",", "")
    return float(cleaned_number_text)


# この関数の役割:
# PDF内の単位を見て、表示用の金額を作ります。
# なぜ必要か:
# 決算資料は「百万円」表記が多く、そのままだと投資家が読む「億円」感覚とずれるためです。
def normalize_value_for_json(value: float, source_text: str, metric_key: str) -> float:
    if metric_key == "eps":
        return value

    if "百万円" in source_text or "単位:百万円" in source_text or "単位 百万円" in source_text:
        return round(value / 100)

    return value


# この関数の役割:
# JSONに入れる数値から、レポート表示用の文字列を作ります。
def format_value_for_display(value: float, source_text: str, metric_key: str) -> str:
    if metric_key == "eps":
        return f"{value:g}円"

    if "百万円" in source_text or "億円" in source_text or "単位:百万円" in source_text or "単位 百万円" in source_text:
        return f"{value:,.0f}億円"

    return f"{value:g}"


# この関数の役割:
# 前年比の表示文字列を作ります。
def format_yoy_for_display(yoy: float | None) -> str:
    if yoy is None:
        return NOT_ACQUIRED

    if yoy > 0:
        return f"+{yoy:.1f}%"

    return f"{yoy:.1f}%"


# この関数の役割:
# 指定した項目名の近くにあるPDFテキストの一部を取り出します。
# なぜ必要か:
# 数値は項目名のすぐ近くに出ることが多いため、関係ない表の数字を拾うリスクを下げられます。
def find_source_text_near_metric(normalized_text: str, aliases: list[str]) -> str:
    lines = normalized_text.splitlines()
    latest_unit_line = ""

    for line_index, line_text in enumerate(lines):
        stripped_line_text = line_text.strip()

        if "単位" in stripped_line_text:
            latest_unit_line = stripped_line_text

        for alias in aliases:
            if alias not in stripped_line_text:
                continue

            source_lines = []

            if latest_unit_line != "":
                source_lines.append(latest_unit_line)

            source_lines.append(stripped_line_text)

            # PDF抽出では、項目名と数値が次の行に分かれることがあります。
            # そのため、該当行に数字が無い場合だけ次の行も根拠に含めます。
            if not re.search(r"\d", stripped_line_text) and line_index + 1 < len(lines):
                source_lines.append(lines[line_index + 1].strip())

            return "\n".join(source_lines).strip()

    return ""


# この関数の役割:
# 項目名近くのテキストから、金額やEPSの候補値を抽出します。
# なぜ必要か:
# AIではなくプログラム側で数値を確定させることで、要約時の取り違えを防ぎます。
def extract_value_from_source_text(source_text: str, metric_key: str) -> float | None:
    if source_text == "":
        return None

    # 前年比のパーセント値を金額やEPSの候補として拾わないように、先に取り除きます。
    source_text_without_percentages = re.sub(r"[-+]?\d+(?:\.\d+)?\s*%", " ", source_text)
    number_pattern = r"[-+]?\d{1,3}(?:,\d{3})+(?:\.\d+)?|[-+]?\d+(?:\.\d+)?"
    number_text_candidates = re.findall(number_pattern, source_text_without_percentages)

    if len(number_text_candidates) == 0:
        return None

    parsed_number_candidates = [parse_number(number_text) for number_text in number_text_candidates]

    # EPSは金額より小さい数字になりやすいため、ページ番号や年度を避けつつ小数も許可します。
    if metric_key == "eps":
        eps_candidates = []

        for number_value in parsed_number_candidates:
            if 1 <= abs(number_value) <= 10000:
                eps_candidates.append(number_value)

        if len(eps_candidates) == 0:
            return None

        return eps_candidates[0]

    amount_candidates = []

    for number_value in parsed_number_candidates:
        # 年度やページ番号のような小さい数字を避け、財務数値らしい候補を優先します。
        if abs(number_value) >= 100:
            amount_candidates.append(number_value)

    if len(amount_candidates) == 0:
        return None

    return amount_candidates[0]


# この関数の役割:
# 項目名近くのテキストから前年比の候補を抽出します。
def extract_yoy_from_source_text(source_text: str) -> float | None:
    if source_text == "":
        return None

    yoy_patterns = [
        r"前年同期比\s*([-+]?\d+(?:\.\d+)?)\s*%",
        r"前年比\s*([-+]?\d+(?:\.\d+)?)\s*%",
        r"増減率\s*([-+]?\d+(?:\.\d+)?)\s*%",
        r"([-+]?\d+(?:\.\d+)?)\s*%",
    ]

    for yoy_pattern in yoy_patterns:
        yoy_candidates = re.findall(yoy_pattern, source_text)

        if len(yoy_candidates) > 0:
            return parse_number(yoy_candidates[-1])

    return None


# この関数の役割:
# 1つの財務項目をPDFテキストから抽出します。
def extract_financial_metric(normalized_text: str, metric_key: str) -> FinancialMetric:
    source_text = find_source_text_near_metric(normalized_text, METRIC_ALIASES[metric_key])
    extracted_value = extract_value_from_source_text(source_text, metric_key)
    extracted_yoy = extract_yoy_from_source_text(source_text)

    normalized_value = None
    display_value = NOT_ACQUIRED

    if extracted_value is not None:
        normalized_value = normalize_value_for_json(
            value=extracted_value,
            source_text=source_text,
            metric_key=metric_key,
        )
        display_value = format_value_for_display(
            value=normalized_value,
            source_text=source_text,
            metric_key=metric_key,
        )

    return FinancialMetric(
        label=METRIC_LABELS[metric_key],
        value=normalized_value,
        display_value=display_value,
        yoy=extracted_yoy,
        display_yoy=format_yoy_for_display(extracted_yoy),
        source_text=source_text if source_text != "" else NOT_ACQUIRED,
    )


# この関数の役割:
# 売上、営業利益、純利益、EPSについて、数値と前年比が同じ根拠テキストから取れているか確認します。
# なぜ必要か:
# 投資分析では、数値と前年比の対応がずれると判断を大きく誤るため、AI要約前に警告を出します。
def validate_financial_metrics(financial_metrics: dict[str, FinancialMetric]) -> list[str]:
    warnings = []

    for metric_key, financial_metric in financial_metrics.items():
        if financial_metric.value is None:
            warnings.append(f"WARNING: {financial_metric.label}の数値が未取得です")

        if financial_metric.yoy is None:
            warnings.append(f"WARNING: {financial_metric.label}の前年比データが未取得です")

        if financial_metric.value is not None and financial_metric.yoy is not None:
            if financial_metric.source_text == NOT_ACQUIRED:
                warnings.append(f"WARNING: {financial_metric.label}の根拠テキストが未取得です")

    return warnings


# この関数の役割:
# PDFテキストから主要な決算数値を抽出し、構造化データにまとめます。
def extract_structured_financial_data(extracted_pdf_text: str) -> StructuredFinancialData:
    normalized_text = normalize_pdf_text(extracted_pdf_text)

    financial_metrics = {
        "sales": extract_financial_metric(normalized_text, "sales"),
        "operating_profit": extract_financial_metric(normalized_text, "operating_profit"),
        "net_income": extract_financial_metric(normalized_text, "net_income"),
        "eps": extract_financial_metric(normalized_text, "eps"),
    }

    warnings = validate_financial_metrics(financial_metrics)

    return StructuredFinancialData(
        sales=financial_metrics["sales"],
        operating_profit=financial_metrics["operating_profit"],
        net_income=financial_metrics["net_income"],
        eps=financial_metrics["eps"],
        warnings=warnings,
    )


# この関数の役割:
# 構造化した財務データをJSON文字列に変換します。
# なぜ必要か:
# AIへ文章ではなくJSONを渡すことで、数値の対応関係を崩しにくくするためです。
def structured_financial_data_to_json(structured_financial_data: StructuredFinancialData) -> str:
    financial_data_dictionary = asdict(structured_financial_data)

    return json.dumps(
        financial_data_dictionary,
        ensure_ascii=False,
        indent=2,
    )


# この関数の役割:
# PDF由来の参考情報をMarkdownで作ります。
# なぜ必要か:
# PDF由来の売上・利益・EPSを正式データに見せないため、数値表ではなく注意書きとして表示します。
def format_source_data_confirmation_as_markdown(
    structured_financial_data: StructuredFinancialData,
) -> str:
    markdown_lines = [
        "## PDF由来の参考情報",
        "",
        "PDFは、事業内容、経営方針、リスク、需要環境などの定性情報を確認するために使います。",
        "PDFから売上・利益・EPSなどの重要数値を機械抽出すると誤検知の可能性があるため、このレポートでは正式データとして表示しません。",
        "売上・利益・EPS・PER・PBR・時価総額などの正式データは、API由来データを優先します。",
    ]

    return "\n".join(markdown_lines)
