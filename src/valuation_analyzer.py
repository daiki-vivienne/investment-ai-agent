# このファイルの役割:
# PERや割安度分析を作ります。
#
# 重要な方針:
# PDF由来のEPSは誤検知リスクがあるため、PER計算には使いません。
# ユーザー指定期間と一致したJ-Quants正式EPSが取れた場合だけ、株価と組み合わせてPERを計算します。

from dataclasses import dataclass
from datetime import datetime
from typing import Any

from src.data_models import (
    EXTERNAL_DATA_REQUIRED,
    FUTURE_IMPLEMENTATION,
    NOT_ACQUIRED as DISPLAY_NOT_ACQUIRED,
    AnalystTargetPriceResult,
    MarketDataResult,
    ValuationAnalysisResult,
)
from src.jquants_client import (
    JQuantsPeriodCheckResult,
    NOT_ACQUIRED as JQUANTS_NOT_ACQUIRED,
    STATUS_ACQUIRED,
)


@dataclass
class PerAnalysisResult:
    # このクラスの役割:
    # PER分析に必要な値、データ元、注意点をまとめます。
    #
    # なぜ必要か:
    # 株価は現在時点、EPSは指定決算期の実績値なので、時点の違いを明示するためです。
    current_price: Any
    eps: Any
    eps_period_type: str
    per: Any
    per_type: str
    status: str
    price_source: str
    eps_source: str
    as_of_date: str
    note: str


# この関数の役割:
# 日本株コードをyfinance用tickerへ変換します。
def convert_stock_code_to_yfinance_ticker(stock_code: str) -> str:
    cleaned_stock_code = stock_code.strip().upper()

    if cleaned_stock_code.endswith(".T"):
        return cleaned_stock_code

    return f"{cleaned_stock_code}.T"


# この関数の役割:
# yfinanceから現在株価を取得します。
#
# なぜ必要か:
# PERは「株価 ÷ EPS」で計算するため、期間一致したEPSとは別に株価が必要です。
# ただしyfinanceは試作用データソースなので、レポートではデータ元と注意点を明示します。
def fetch_current_price_from_yfinance(stock_code: str) -> tuple[Any, str]:
    try:
        import yfinance as yf
    except ModuleNotFoundError as error:
        raise ValueError(
            "yfinanceがインストールされていません。"
            "pip install -r requirements.txt を実行してください。"
        ) from error

    ticker_symbol = convert_stock_code_to_yfinance_ticker(stock_code)
    stock_ticker = yf.Ticker(ticker_symbol)
    info_dictionary = stock_ticker.info

    current_price = info_dictionary.get("currentPrice") or info_dictionary.get("regularMarketPrice")

    if current_price is None:
        return JQUANTS_NOT_ACQUIRED, "currentPrice / regularMarketPrice"

    return current_price, "currentPrice / regularMarketPrice"


# この関数の役割:
# J-Quants正式EPSとyfinance株価から、現在株価ベースの実績PERを計算します。
#
# なぜ必要か:
# PDF由来のEPSを使うと脚注やNon-GAAP値を誤って拾う可能性があるため、
# 期間一致したJ-Quants正式EPSだけをPER計算に使います。
def calculate_per_analysis(
    stock_code: str | None,
    period_check_result: JQuantsPeriodCheckResult | None,
    market_data_result: MarketDataResult | None = None,
) -> PerAnalysisResult | None:
    eps_period_type = period_check_result.requested_period_type if period_check_result is not None else "-"

    if stock_code is None or stock_code.strip() == "":
        return None

    if period_check_result is None or not period_check_result.is_period_matched:
        return PerAnalysisResult(
            current_price=JQUANTS_NOT_ACQUIRED,
            eps=JQUANTS_NOT_ACQUIRED,
            eps_period_type=eps_period_type,
            per=JQUANTS_NOT_ACQUIRED,
            per_type="現在株価ベースの実績PER",
            status="未取得",
            price_source="yfinance",
            eps_source="J-Quants",
            as_of_date="-",
            note="ユーザー指定期間と一致するJ-Quants正式EPSが未取得のため、PERは計算しません。",
        )

    eps_item = period_check_result.formal_data_items.get("eps")

    if eps_item is None or eps_item.status != STATUS_ACQUIRED:
        return PerAnalysisResult(
            current_price=JQUANTS_NOT_ACQUIRED,
            eps=JQUANTS_NOT_ACQUIRED,
            eps_period_type=eps_period_type,
            per=JQUANTS_NOT_ACQUIRED,
            per_type="現在株価ベースの実績PER",
            status="未取得",
            price_source="yfinance",
            eps_source="J-Quants",
            as_of_date="-",
            note="J-Quants正式EPSが未取得のため、PERは計算しません。",
        )

    try:
        eps_value = float(eps_item.value)
    except (TypeError, ValueError):
        return PerAnalysisResult(
            current_price=JQUANTS_NOT_ACQUIRED,
            eps=eps_item.value,
            eps_period_type=eps_period_type,
            per=JQUANTS_NOT_ACQUIRED,
            per_type="現在株価ベースの実績PER",
            status="未取得",
            price_source="yfinance",
            eps_source="J-Quants",
            as_of_date="-",
            note="J-Quants正式EPSを数値に変換できないため、PERは計算しません。",
        )

    if eps_value <= 0:
        return PerAnalysisResult(
            current_price=JQUANTS_NOT_ACQUIRED,
            eps=eps_item.value,
            eps_period_type=eps_period_type,
            per=JQUANTS_NOT_ACQUIRED,
            per_type="現在株価ベースの実績PER",
            status="未取得",
            price_source="yfinance",
            eps_source="J-Quants",
            as_of_date="-",
            note="EPSが0以下のため、PERは計算しません。",
        )

    if market_data_result is not None and market_data_result.current_stock_price is not None:
        current_price = market_data_result.current_stock_price
        raw_price_field_name = "history(period=5d) latest Close"
    else:
        try:
            current_price, raw_price_field_name = fetch_current_price_from_yfinance(stock_code)
        except ValueError as error:
            return PerAnalysisResult(
                current_price=JQUANTS_NOT_ACQUIRED,
                eps=eps_item.value,
                eps_period_type=eps_period_type,
                per=JQUANTS_NOT_ACQUIRED,
                per_type="現在株価ベースの実績PER",
                status="未取得",
                price_source="yfinance",
                eps_source=f"J-Quants {eps_item.raw_field_name}",
                as_of_date="-",
                note=f"株価取得に失敗したため、PERは計算しません。詳細: {error}",
            )

    if current_price == JQUANTS_NOT_ACQUIRED:
        return PerAnalysisResult(
            current_price=JQUANTS_NOT_ACQUIRED,
            eps=eps_item.value,
            eps_period_type=eps_period_type,
            per=JQUANTS_NOT_ACQUIRED,
            per_type="現在株価ベースの実績PER",
            status="未取得",
            price_source="yfinance",
            eps_source=f"J-Quants {eps_item.raw_field_name}",
            as_of_date="-",
            note="yfinanceから現在株価を取得できなかったため、PERは計算しません。",
        )

    per_value = float(current_price) / eps_value
    non_fy_note = ""

    if eps_period_type.upper() != "FY":
        non_fy_note = (
            f" このEPSは{eps_period_type}の実績EPSであり、"
            "通期実績EPSや予想EPSではありません。"
        )

    return PerAnalysisResult(
        current_price=current_price,
        eps=eps_value,
        eps_period_type=eps_period_type,
        per=round(per_value, 2),
        per_type="現在株価ベースの実績PER",
        status="取得済み",
        price_source=f"yfinance {raw_price_field_name}",
        eps_source=f"J-Quants {eps_item.raw_field_name}",
        as_of_date=f"取得日時: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        note=(
            "現在株価ベースの実績PERです。株価はyfinance由来の同一取得結果、"
            "EPSはユーザー指定期間と一致したJ-Quants実績EPSを使っています。"
            "株価時点とEPS対象期間は異なります。"
            f"{non_fy_note}"
        ),
    )


# この関数の役割:
# API由来の株価とEPSから実績PERを計算します。
#
# なぜ必要か:
# V2で作った将来拡張用の投資判断支援セクションを残すためです。
# こちらはyfinance由来の参考市場データを表示するための補助で、正式PERは上のcalculate_per_analysisを使います。
def calculate_actual_per(current_stock_price: float | None, eps: float | None) -> str:
    if current_stock_price is None:
        return DISPLAY_NOT_ACQUIRED

    if eps is None:
        return DISPLAY_NOT_ACQUIRED

    if eps <= 0:
        return DISPLAY_NOT_ACQUIRED

    actual_per = current_stock_price / eps

    return f"{actual_per:.1f}倍"


# この関数の役割:
# 将来拡張用のPER・割安度分析結果を作ります。
#
# なぜ必要か:
# 予想PER、業界平均PER、割安判定など、今後APIを増やしたときに同じ場所へ拡張できるようにするためです。
def create_valuation_analysis(
    market_data_result: MarketDataResult | None = None,
) -> ValuationAnalysisResult:
    current_stock_price = DISPLAY_NOT_ACQUIRED
    eps = "PER分析セクションを参照"

    if market_data_result is not None:
        current_stock_price = market_data_result.display_current_stock_price

    actual_per = "PER分析セクションを参照"

    note_text = (
        "この表は将来拡張用の参考セクションです。"
        "現在の正式なPER計算結果は、上部の「PER分析」セクションを確認してください。"
        "この参考セクションでは、yfinanceのEPSやPDF由来EPSを使った別計算は行いません。"
        "予想PER、業界平均PER、割安判定は今後の外部データ連携で拡張します。"
    )

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
# 将来拡張用のPER分析結果をMarkdown形式へ変換します。
def format_valuation_analysis_as_markdown(valuation_analysis_result: ValuationAnalysisResult) -> str:
    return f"""
## 参考PER・割安度分析

| 項目 | 内容 |
| ---- | ---- |
| 現在株価 API由来 | {valuation_analysis_result.current_stock_price} |
| EPS | {valuation_analysis_result.eps} |
| 実績PER | {valuation_analysis_result.actual_per} |
| 予想PER | {valuation_analysis_result.forecast_per} |
| 業界平均PER | {valuation_analysis_result.industry_average_per} |
| 割安/普通/割高の判定 | {valuation_analysis_result.valuation_judgement} |

補足: {valuation_analysis_result.note}
""".strip()


# この関数の役割:
# 投資銀行や証券会社の目標株価データ取得口を用意します。
#
# なぜ必要か:
# 現時点では取得元を確定していないため、ダミーデータを入れず「将来実装予定」と明示します。
def create_institutional_target_price_analysis() -> list[AnalystTargetPriceResult]:
    target_price_results = [
        AnalystTargetPriceResult(
            institution_name="Goldman Sachs",
            target_price=DISPLAY_NOT_ACQUIRED,
            rating=DISPLAY_NOT_ACQUIRED,
            source=DISPLAY_NOT_ACQUIRED,
            note=FUTURE_IMPLEMENTATION,
        ),
        AnalystTargetPriceResult(
            institution_name="Morgan Stanley",
            target_price=DISPLAY_NOT_ACQUIRED,
            rating=DISPLAY_NOT_ACQUIRED,
            source=DISPLAY_NOT_ACQUIRED,
            note=FUTURE_IMPLEMENTATION,
        ),
        AnalystTargetPriceResult(
            institution_name="JP Morgan",
            target_price=DISPLAY_NOT_ACQUIRED,
            rating=DISPLAY_NOT_ACQUIRED,
            source=DISPLAY_NOT_ACQUIRED,
            note=FUTURE_IMPLEMENTATION,
        ),
    ]

    return target_price_results


# この関数の役割:
# 有力機関の目標株価データをMarkdown表へ変換します。
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
