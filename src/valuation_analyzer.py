# このファイルの役割:
# PERや割安度の分析結果を作ります。

from src.data_models import (
    EXTERNAL_DATA_REQUIRED,
    FUTURE_IMPLEMENTATION,
    NOT_ACQUIRED,
    AnalystTargetPriceResult,
    MarketDataResult,
    ValuationAnalysisResult,
)


# この関数の役割:
# PER分析に必要な外部データがまだ無い状態の結果を作ります。
# なぜ必要か:
# 決算PDFだけでは現在株価、予想EPS、業界平均PERを正確に取得できないため、推測で埋めない設計にします。
def calculate_actual_per(current_stock_price: float | None, eps: float | None) -> str:
    # この関数の役割:
    # API由来の現在株価とAPI由来のEPSから実績PERを計算します。
    # なぜ必要か:
    # PDF由来EPSは誤検知リスクがあるため、PER計算にはAPI由来EPSだけを使うためです。
    if current_stock_price is None:
        return NOT_ACQUIRED

    if eps is None:
        return NOT_ACQUIRED

    if eps <= 0:
        return NOT_ACQUIRED

    actual_per = current_stock_price / eps

    return f"{actual_per:.1f}倍"


def create_valuation_analysis(
    market_data_result: MarketDataResult | None = None,
) -> ValuationAnalysisResult:
    current_stock_price = NOT_ACQUIRED
    eps = NOT_ACQUIRED

    if market_data_result is not None:
        current_stock_price = market_data_result.display_current_stock_price
        eps = market_data_result.display_eps

    actual_per = calculate_actual_per(
        current_stock_price=market_data_result.current_stock_price if market_data_result is not None else None,
        eps=market_data_result.eps if market_data_result is not None else None,
    )

    note_text = "実績PERは、API由来の現在株価とAPI由来のEPSが取得できた場合だけ計算します。PDF由来のEPSは計算に使いません。"

    if market_data_result is not None and market_data_result.note != "":
        note_text = f"{note_text} APIデータ: {market_data_result.note}"

    return ValuationAnalysisResult(
        current_stock_price=current_stock_price,
        eps=eps,
        actual_per=actual_per,
        forecast_per=EXTERNAL_DATA_REQUIRED,
        industry_average_per=EXTERNAL_DATA_REQUIRED,
        valuation_judgement=EXTERNAL_DATA_REQUIRED,
        note=note_text,
    )


# この関数の役割:
# PER分析結果をMarkdown形式に変換します。
def format_valuation_analysis_as_markdown(valuation_analysis_result: ValuationAnalysisResult) -> str:
    return f"""
## PER分析

| 項目 | 内容 |
| ---- | ---- |
| 現在株価 API由来 | {valuation_analysis_result.current_stock_price} |
| EPS API由来 | {valuation_analysis_result.eps} |
| 実績PER API由来 | {valuation_analysis_result.actual_per} |
| 予想PER | {valuation_analysis_result.forecast_per} |
| 業界平均PER | {valuation_analysis_result.industry_average_per} |
| 割安/普通/割高の判定 | {valuation_analysis_result.valuation_judgement} |

補足: {valuation_analysis_result.note}
""".strip()


# この関数の役割:
# 投資銀行や証券会社の目標株価データの取得口を用意します。
# なぜ必要か:
# 現時点では取得元が未接続なので、ダミーデータを使わず「将来実装予定」と明示します。
def create_institutional_target_price_analysis() -> list[AnalystTargetPriceResult]:
    target_price_results = [
        AnalystTargetPriceResult(
            institution_name="Goldman Sachs",
            target_price=NOT_ACQUIRED,
            rating=NOT_ACQUIRED,
            source=NOT_ACQUIRED,
            note=FUTURE_IMPLEMENTATION,
        ),
        AnalystTargetPriceResult(
            institution_name="Morgan Stanley",
            target_price=NOT_ACQUIRED,
            rating=NOT_ACQUIRED,
            source=NOT_ACQUIRED,
            note=FUTURE_IMPLEMENTATION,
        ),
        AnalystTargetPriceResult(
            institution_name="JP Morgan",
            target_price=NOT_ACQUIRED,
            rating=NOT_ACQUIRED,
            source=NOT_ACQUIRED,
            note=FUTURE_IMPLEMENTATION,
        ),
    ]

    return target_price_results


# この関数の役割:
# 有力機関の目標株価データをMarkdown表に変換します。
def format_institutional_target_price_as_markdown(
    target_price_results: list[AnalystTargetPriceResult],
) -> str:
    markdown_lines = [
        "## 有力機関の目標株価",
        "",
        "現時点では外部データ取得を実装していないため、ダミーデータは表示しません。",
        "",
        "| 機関 | 目標株価 | レーティング | 情報源 | 補足 |",
        "| ---- | ---- | ---- | ---- | ---- |",
    ]

    for target_price_result in target_price_results:
        markdown_lines.append(
            "| "
            f"{target_price_result.institution_name} | "
            f"{target_price_result.target_price} | "
            f"{target_price_result.rating} | "
            f"{target_price_result.source} | "
            f"{target_price_result.note} |"
        )

    return "\n".join(markdown_lines)
