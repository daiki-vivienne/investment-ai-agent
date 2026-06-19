# このファイルの役割:
# CLIや将来のDiscord Botから共通で使える、レポート生成の中心処理をまとめます。
#
# なぜ必要か:
# main.pyに処理を集めすぎると、Discord Botから同じ処理を呼び出しにくくなります。
# このファイルに共通処理を置くことで、CLIでもBotでも同じgenerate_report()を使えます。

from dataclasses import asdict, dataclass
import json
from pathlib import Path
from typing import Callable

from src.api_report_formatter import (
    build_api_context_for_ai,
    build_formal_performance_summary_markdown,
    build_per_analysis_markdown,
    build_period_consistency_markdown,
)
from src.ai_analyzer import analyze_financial_report
from src.ai_output_guard import guard_ai_analysis_markdown
from src.jquants_client import check_jquants_period_consistency
from src.market_analyzer import create_market_size_analysis, format_market_size_analysis_as_markdown
from src.market_data_client import fetch_market_data
from src.numeric_extractor import extract_structured_financial_data, format_source_data_confirmation_as_markdown
from src.pdf_reader import extract_text_from_pdf
from src.peer_comparison import create_peer_comparison, format_peer_comparison_as_markdown
from src.report_writer import save_markdown_report
from src.scenario_analyzer import create_scenario_analysis, format_scenario_analysis_as_markdown
from src.valuation_analyzer import (
    calculate_per_analysis,
    create_institutional_target_price_analysis,
    create_valuation_analysis,
    format_institutional_target_price_as_markdown,
    format_valuation_analysis_as_markdown,
)


@dataclass
class ReportGenerationResult:
    # このクラスの役割:
    # レポート生成の結果を、CLIやDiscord Botが扱いやすい形で返します。
    status: str
    message: str
    report_file_path: Path
    markdown_text: str


# この型の役割:
# CLIでは途中経過をprintし、Discord Botでは処理中メッセージ送信などに差し替えられるようにします。
ProgressCallback = Callable[[str], None]


# この関数の役割:
# API由来データをJSON文字列に変換します。
# なぜ必要か:
# AIへ渡す投資指標の出所を明確にし、PDF由来数値と混ぜないためです。
def market_data_result_to_json(market_data_result) -> str:
    return json.dumps(asdict(market_data_result), ensure_ascii=False, indent=2)


# この関数の役割:
# yfinance由来の市場データをMarkdown表にします。
def format_api_data_as_markdown(market_data_result) -> str:
    return f"""
## yfinance由来の参考市場データ

| 項目 | 内容 |
| --- | --- |
| 入力証券コード | {market_data_result.requested_ticker} |
| API用ticker | {market_data_result.normalized_ticker} |
| 現在株価 | {market_data_result.display_current_stock_price} |
| PBR | {market_data_result.display_pbr} |
| 時価総額 | {market_data_result.display_market_cap} |
| データ取得元 | {market_data_result.data_source} |
| 補足 | {market_data_result.note} |

このセクションは試作用の市場データです。売上、利益、EPSなどの正式な財務データは、期間一致したJ-Quantsデータを優先します。
""".strip()


# この関数の役割:
# AI分析の後ろに、将来拡張しやすい投資判断支援セクションを追加します。
# なぜ必要か:
# PDFだけでは取れないデータを推測せず、未取得または外部データが必要と明示するためです。
def build_investment_support_markdown(market_data_result) -> str:
    valuation_analysis_result = create_valuation_analysis(
        market_data_result=market_data_result,
    )
    scenario_analysis_results = create_scenario_analysis()
    target_price_results = create_institutional_target_price_analysis()
    market_size_results = create_market_size_analysis()
    peer_comparison_results = create_peer_comparison()

    markdown_sections = [
        "# 投資判断支援セクション",
        "",
        "このセクションは、将来の外部データ連携を見据えた分析土台です。",
        "取得できないデータは、推測せず「未取得」または「外部データが必要」と表示します。",
        "",
        format_valuation_analysis_as_markdown(valuation_analysis_result),
        "",
        format_scenario_analysis_as_markdown(scenario_analysis_results),
        "",
        format_institutional_target_price_as_markdown(target_price_results),
        "",
        format_market_size_analysis_as_markdown(market_size_results),
        "",
        format_peer_comparison_as_markdown(peer_comparison_results),
    ]

    return "\n".join(markdown_sections)


# この関数の役割:
# 複数のMarkdownセクションを1つのレポートにまとめます。
def combine_report_sections(
    pdf_reference_markdown: str,
    period_consistency_markdown: str,
    formal_performance_summary_markdown: str,
    per_analysis_markdown: str,
    api_data_markdown: str,
    ai_analysis_markdown: str,
    investment_support_markdown: str,
) -> str:
    return (
        f"{pdf_reference_markdown.strip()}"
        f"\n\n---\n\n"
        f"{period_consistency_markdown.strip()}"
        f"\n\n"
        f"{formal_performance_summary_markdown.strip()}"
        f"\n\n"
        f"{per_analysis_markdown.strip()}"
        f"\n\n---\n\n"
        f"{api_data_markdown.strip()}"
        f"\n\n---\n\n"
        f"{ai_analysis_markdown.strip()}"
        f"\n\n---\n\n"
        f"{investment_support_markdown.strip()}\n"
    )


# この関数の役割:
# 途中経過を通知します。通知先がない場合は何もしません。
def notify_progress(progress_callback: ProgressCallback | None, message: str) -> None:
    if progress_callback is None:
        return

    progress_callback(message)


# この関数の役割:
# PDF読み込みからMarkdown保存までの中心処理を実行します。
#
# なぜ必要か:
# CLIとDiscord Botの両方が、この関数を呼ぶだけで同じレポート生成処理を使えるようにするためです。
def generate_report(
    pdf_path: str | Path,
    output_dir: str | Path,
    openai_api_key: str,
    openai_model: str,
    jquants_api_key: str | None,
    stock_code: str | None = None,
    ticker: str | None = None,
    period_type: str | None = None,
    fiscal_year_end: str | None = None,
    progress_callback: ProgressCallback | None = None,
) -> ReportGenerationResult:
    pdf_file_path = Path(pdf_path)
    report_output_directory = Path(output_dir)
    ticker_for_market_data = ticker or stock_code or ""

    notify_progress(progress_callback, f"PDFを読み込んでいます: {pdf_file_path}")
    extracted_pdf_text = extract_text_from_pdf(pdf_file_path)

    notify_progress(progress_callback, "PDF由来の参考情報を整理しています...")
    structured_financial_data = extract_structured_financial_data(extracted_pdf_text)

    for warning_message in structured_financial_data.warnings:
        notify_progress(progress_callback, f"{warning_message} PDF由来の数値は正式データとして扱いません。")

    notify_progress(progress_callback, "yfinance由来の参考市場データを取得しています...")
    market_data_result = fetch_market_data(ticker=ticker_for_market_data)
    api_market_data_json = market_data_result_to_json(market_data_result)

    notify_progress(progress_callback, "J-Quants APIデータの期間整合性を確認しています...")
    period_check_result = check_jquants_period_consistency(
        api_key=jquants_api_key,
        stock_code=stock_code,
        period_type=period_type,
        fiscal_year_end=fiscal_year_end,
    )
    api_context_markdown = build_api_context_for_ai(period_check_result)
    period_consistency_markdown = build_period_consistency_markdown(period_check_result)
    formal_performance_summary_markdown = build_formal_performance_summary_markdown(period_check_result)

    notify_progress(progress_callback, "PER分析を確認しています...")
    per_analysis_result = calculate_per_analysis(
        stock_code=stock_code,
        period_check_result=period_check_result,
        market_data_result=market_data_result,
    )
    per_analysis_markdown = build_per_analysis_markdown(per_analysis_result)
    api_context_with_per_markdown = (
        f"{api_context_markdown}\n\n"
        f"yfinance由来の参考市場データ:\n{api_market_data_json}\n\n"
        f"PER分析:\n{per_analysis_markdown}"
    )

    notify_progress(progress_callback, "AIに決算分析を依頼しています。少し時間がかかる場合があります...")
    ai_analysis_markdown = analyze_financial_report(
        extracted_pdf_text=extracted_pdf_text,
        api_market_data_json=api_market_data_json,
        openai_api_key=openai_api_key,
        openai_model=openai_model,
        api_context_markdown=api_context_with_per_markdown,
    )
    guarded_analysis_markdown = guard_ai_analysis_markdown(
        analysis_markdown=ai_analysis_markdown,
        period_check_result=period_check_result,
    )

    notify_progress(progress_callback, "投資判断支援セクションを作成しています...")
    pdf_reference_markdown = format_source_data_confirmation_as_markdown(
        structured_financial_data=structured_financial_data,
    )
    api_data_markdown = format_api_data_as_markdown(market_data_result=market_data_result)
    investment_support_markdown = build_investment_support_markdown(market_data_result=market_data_result)
    full_report_markdown = combine_report_sections(
        pdf_reference_markdown=pdf_reference_markdown,
        period_consistency_markdown=period_consistency_markdown,
        formal_performance_summary_markdown=formal_performance_summary_markdown,
        per_analysis_markdown=per_analysis_markdown,
        api_data_markdown=api_data_markdown,
        ai_analysis_markdown=guarded_analysis_markdown,
        investment_support_markdown=investment_support_markdown,
    )

    notify_progress(progress_callback, "Markdownレポートを保存しています...")
    saved_report_path = save_markdown_report(
        markdown_text=full_report_markdown,
        source_pdf_path=pdf_file_path,
        output_directory=report_output_directory,
    )

    return ReportGenerationResult(
        status="success",
        message="分析レポートの作成が完了しました。",
        report_file_path=saved_report_path,
        markdown_text=full_report_markdown,
    )
