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
    # 実績EPS、会社予想EPS、次期予想EPS候補は意味が違うため、
    # それぞれのPERを混同しないように行ごとの値・データ元・補足を持たせます。
    current_price: Any
    current_price_source: str
    current_price_note: str
    eps: Any
    eps_source: str
    eps_note: str
    eps_period_type: str
    actual_per: Any
    actual_per_source: str
    actual_per_note: str
    forecast_eps: Any
    forecast_eps_source: str
    forecast_eps_note: str
    forecast_per: Any
    forecast_per_source: str
    forecast_per_note: str
    next_forecast_eps: Any
    next_forecast_eps_source: str
    next_forecast_eps_note: str
    next_forecast_per: Any
    next_forecast_per_source: str
    next_forecast_per_note: str
    status: str
    as_of_date: str
    note: str
    warning_message: str


# この関数の役割:
# PER分析の数値を読みやすい円表示にします。
def format_yen_value(value: float) -> str:
    return f"{value:,.2f}円"


# この関数の役割:
# PER分析の倍率を読みやすい表示にします。
def format_per_value(value: float) -> str:
    return f"{value:,.2f}倍"


# この関数の役割:
# J-QuantsのDataItemをfloatへ変換します。
def convert_data_item_to_float(value: Any) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


# この関数の役割:
# EPSと現在株価からPERを計算し、計算できない場合は理由を返します。
#
# なぜ必要か:
# EPSが未取得、0、赤字、文字列などの場合に無理にPERを出すと誤解を招くためです。
def calculate_per_display(
    current_price: float | None,
    eps_value: float | None,
    eps_display_name: str,
) -> tuple[str, str, str]:
    if current_price is None:
        return JQUANTS_NOT_ACQUIRED, "計算値", "現在株価が未取得のため計算しません。"

    if eps_value is None:
        return JQUANTS_NOT_ACQUIRED, "計算値", f"{eps_display_name}が未取得または数値変換できないため計算しません。"

    if eps_value < 0:
        return JQUANTS_NOT_ACQUIRED, "計算値", "赤字のためPER算出対象外です。"

    if eps_value == 0:
        return JQUANTS_NOT_ACQUIRED, "計算値", f"{eps_display_name}が0のため計算しません。"

    per_value = current_price / eps_value
    note = f"現在株価 ÷ {eps_display_name}"

    if per_value > 1000:
        note = f"WARNING: PERが1000倍を超えています。異常値の可能性があります。{note}"

    return format_per_value(per_value), "計算値", note


# この関数の役割:
# J-Quants正式データ項目から、表示値・データ元・補足・数値を作ります。
def build_eps_display_parts(
    period_check_result: JQuantsPeriodCheckResult,
    item_key: str,
    display_name: str,
) -> tuple[str, str, str, float | None]:
    data_item = period_check_result.formal_data_items.get(item_key)

    if data_item is None or data_item.status != STATUS_ACQUIRED:
        source_name = {
            "eps": "J-Quants EPS",
            "forecast_eps": "J-Quants FEPS",
            "next_forecast_eps": "J-Quants NxFEPS",
        }.get(item_key, "J-Quants")
        return JQUANTS_NOT_ACQUIRED, source_name, f"{display_name}が未取得のため計算しません。", None

    eps_value = convert_data_item_to_float(data_item.value)

    if eps_value is None:
        return (
            JQUANTS_NOT_ACQUIRED,
            f"J-Quants {data_item.raw_field_name}",
            f"{display_name}を数値に変換できないため計算しません。",
            None,
        )

    note = "期間一致した正式データ"

    if item_key == "forecast_eps":
        note = "会社予想EPS候補です。J-Quantsのフィールド定義確認が必要です。"

    if item_key == "next_forecast_eps":
        note = "次期予想EPS候補です。J-Quantsのフィールド定義確認が必要です。"

    return format_yen_value(eps_value), f"J-Quants {data_item.raw_field_name}", note, eps_value


# この関数の役割:
# 期間不一致や株価未取得時のPER分析結果を作ります。
def create_unavailable_per_analysis_result(
    eps_period_type: str,
    note: str,
    current_price: Any = JQUANTS_NOT_ACQUIRED,
    current_price_source: str = "yfinance",
    current_price_note: str = "PER計算に使える現在株価が未取得です。",
) -> PerAnalysisResult:
    return PerAnalysisResult(
        current_price=current_price,
        current_price_source=current_price_source,
        current_price_note=current_price_note,
        eps=JQUANTS_NOT_ACQUIRED,
        eps_source="J-Quants EPS",
        eps_note="期間一致データ未取得のためPER分析は保留します。",
        eps_period_type=eps_period_type,
        actual_per=JQUANTS_NOT_ACQUIRED,
        actual_per_source="計算値",
        actual_per_note="期間一致データ未取得のためPER分析は保留します。",
        forecast_eps=JQUANTS_NOT_ACQUIRED,
        forecast_eps_source="J-Quants FEPS",
        forecast_eps_note="期間一致データ未取得のためPER分析は保留します。",
        forecast_per=JQUANTS_NOT_ACQUIRED,
        forecast_per_source="計算値",
        forecast_per_note="期間一致データ未取得のためPER分析は保留します。",
        next_forecast_eps=JQUANTS_NOT_ACQUIRED,
        next_forecast_eps_source="J-Quants NxFEPS",
        next_forecast_eps_note="期間一致データ未取得のためPER分析は保留します。",
        next_forecast_per=JQUANTS_NOT_ACQUIRED,
        next_forecast_per_source="計算値",
        next_forecast_per_note="期間一致データ未取得のためPER分析は保留します。",
        status="未取得",
        as_of_date="-",
        note=note,
        warning_message="",
    )


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
        current_price_display = JQUANTS_NOT_ACQUIRED
        current_price_source = "yfinance"
        current_price_note = "現在株価は未取得です。期間一致データもないためPER分析は保留します。"

        if market_data_result is not None and market_data_result.current_stock_price is not None:
            current_price_display = format_yen_value(float(market_data_result.current_stock_price))
            current_price_source = "yfinance history(period=5d) latest Close"
            current_price_note = (
                "遅延価格または直近価格の可能性があります。"
                "参考表示のみで、期間一致データ未取得のためPER計算には使いません。"
            )

        return create_unavailable_per_analysis_result(
            eps_period_type=eps_period_type,
            note="期間一致データ未取得のためPER分析は保留します。",
            current_price=current_price_display,
            current_price_source=current_price_source,
            current_price_note=current_price_note,
        )

    if market_data_result is not None and market_data_result.current_stock_price is not None:
        current_price = market_data_result.current_stock_price
        raw_price_field_name = "history(period=5d) latest Close"
    else:
        try:
            current_price, raw_price_field_name = fetch_current_price_from_yfinance(stock_code)
        except ValueError as error:
            return create_unavailable_per_analysis_result(
                eps_period_type=eps_period_type,
                note=f"株価取得に失敗したため、PERは計算しません。詳細: {error}",
            )

    if current_price == JQUANTS_NOT_ACQUIRED:
        return create_unavailable_per_analysis_result(
            eps_period_type=eps_period_type,
            note="yfinanceから現在株価を取得できなかったため、PERは計算しません。",
        )

    current_price_value = float(current_price)
    current_price_display = format_yen_value(current_price_value)
    current_price_source = f"yfinance {raw_price_field_name}"
    current_price_note = "遅延価格または直近価格の可能性があります。"

    eps_display, eps_source, eps_note, eps_value = build_eps_display_parts(
        period_check_result=period_check_result,
        item_key="eps",
        display_name="実績EPS",
    )
    forecast_eps_display, forecast_eps_source, forecast_eps_note, forecast_eps_value = build_eps_display_parts(
        period_check_result=period_check_result,
        item_key="forecast_eps",
        display_name="予想EPS",
    )
    next_forecast_eps_display, next_forecast_eps_source, next_forecast_eps_note, next_forecast_eps_value = build_eps_display_parts(
        period_check_result=period_check_result,
        item_key="next_forecast_eps",
        display_name="次期予想EPS候補",
    )

    actual_per, actual_per_source, actual_per_note = calculate_per_display(
        current_price=current_price_value,
        eps_value=eps_value,
        eps_display_name="実績EPS",
    )
    forecast_per, forecast_per_source, forecast_per_note = calculate_per_display(
        current_price=current_price_value,
        eps_value=forecast_eps_value,
        eps_display_name="予想EPS",
    )
    next_forecast_per, next_forecast_per_source, next_forecast_per_note = calculate_per_display(
        current_price=current_price_value,
        eps_value=next_forecast_eps_value,
        eps_display_name="次期予想EPS候補",
    )

    warning_messages = []

    for note_text in [actual_per_note, forecast_per_note, next_forecast_per_note]:
        if "WARNING" in note_text:
            warning_messages.append(note_text)

    non_fy_note = ""

    if eps_period_type.upper() != "FY":
        non_fy_note = f" このEPSは{eps_period_type}の実績EPSであり、通期実績EPSや予想EPSではありません。"

    return PerAnalysisResult(
        current_price=current_price_display,
        current_price_source=current_price_source,
        current_price_note=current_price_note,
        eps=eps_display,
        eps_source=eps_source,
        eps_note=f"{eps_note}{non_fy_note}",
        eps_period_type=eps_period_type,
        actual_per=actual_per,
        actual_per_source=actual_per_source,
        actual_per_note=actual_per_note,
        forecast_eps=forecast_eps_display,
        forecast_eps_source=forecast_eps_source,
        forecast_eps_note=forecast_eps_note,
        forecast_per=forecast_per,
        forecast_per_source=forecast_per_source,
        forecast_per_note=forecast_per_note,
        next_forecast_eps=next_forecast_eps_display,
        next_forecast_eps_source=next_forecast_eps_source,
        next_forecast_eps_note=next_forecast_eps_note,
        next_forecast_per=next_forecast_per,
        next_forecast_per_source=next_forecast_per_source,
        next_forecast_per_note=next_forecast_per_note,
        status="取得済み",
        as_of_date=f"取得日時: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        note=(
            "PDF由来EPSとyfinance由来EPSは使いません。"
            "期間一致したJ-Quants EPS/FEPS/NxFEPSとyfinance現在株価だけを使います。"
        ),
        warning_message=" / ".join(warning_messages),
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
        forecast_per="PER分析セクションを参照",
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
