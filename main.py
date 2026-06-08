# このファイルの役割:
# アプリ全体の入り口です。PDFを読み込み、API由来データと期間整合性を確認し、AI分析レポートを保存します。

from pathlib import Path
import argparse
from dataclasses import asdict
import json
import sys

from src.api_report_formatter import (
    build_api_context_for_ai,
    build_formal_performance_summary_markdown,
    build_per_analysis_markdown,
    build_period_consistency_markdown,
)
from src.ai_analyzer import analyze_financial_report
from src.ai_output_guard import guard_ai_analysis_markdown
from src.config import load_application_config
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


# この関数の役割:
# コマンドラインから受け取る引数を定義します。
# なぜ必要か:
# PDFから決算期を推測せず、ユーザーが指定した期間を正として扱うためです。
def create_argument_parser() -> argparse.ArgumentParser:
    argument_parser = argparse.ArgumentParser(
        description="決算PDFをAIで分析し、投資判断材料のMarkdownレポートを作成します。"
    )

    argument_parser.add_argument(
        "pdf_path",
        help="分析したい決算PDFファイルのパス。例: data/pdfs/sample.pdf",
    )

    argument_parser.add_argument(
        "--output-dir",
        default="data/reports",
        help="Markdownレポートの保存先フォルダ。初期値: data/reports",
    )

    argument_parser.add_argument(
        "--stock-code",
        default=None,
        help="J-Quantsで財務データを探す証券コード。例: 285A",
    )

    argument_parser.add_argument(
        "--period-type",
        default=None,
        help="ユーザーが正とする決算期間。PDFから推測せず、ここで指定します。例: FY, 3Q",
    )

    argument_parser.add_argument(
        "--fiscal-year-end",
        default=None,
        help="ユーザーが正とする会計年度末。PDFから推測せず、ここで指定します。例: 2026-03-31",
    )

    argument_parser.add_argument(
        "--ticker",
        default="",
        help="yfinanceの株価取得に使う証券コード。未指定なら --stock-code を使います。例: 285A",
    )

    return argument_parser


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
# 実際の処理を順番に実行します。
def run_application() -> None:
    argument_parser = create_argument_parser()
    command_line_arguments = argument_parser.parse_args()

    pdf_file_path = Path(command_line_arguments.pdf_path)
    report_output_directory = Path(command_line_arguments.output_dir)
    stock_code = command_line_arguments.stock_code
    ticker = command_line_arguments.ticker or stock_code or ""

    try:
        print("設定を読み込んでいます...")
        application_config = load_application_config()

        print(f"PDFを読み込んでいます: {pdf_file_path}")
        extracted_pdf_text = extract_text_from_pdf(pdf_file_path)

        print("PDF由来の参考情報を整理しています...")
        structured_financial_data = extract_structured_financial_data(extracted_pdf_text)

        for warning_message in structured_financial_data.warnings:
            print(f"{warning_message} PDF由来の数値は正式データとして扱いません。")

        print("yfinance由来の参考市場データを取得しています...")
        market_data_result = fetch_market_data(ticker=ticker)
        api_market_data_json = market_data_result_to_json(market_data_result)

        print("J-Quants APIデータの期間整合性を確認しています...")
        period_check_result = check_jquants_period_consistency(
            api_key=application_config.jquants_api_key,
            stock_code=stock_code,
            period_type=command_line_arguments.period_type,
            fiscal_year_end=command_line_arguments.fiscal_year_end,
        )
        api_context_markdown = build_api_context_for_ai(period_check_result)
        period_consistency_markdown = build_period_consistency_markdown(period_check_result)
        formal_performance_summary_markdown = build_formal_performance_summary_markdown(period_check_result)

        print("PER分析を確認しています...")
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

        print("AIに決算分析を依頼しています。少し時間がかかる場合があります...")
        ai_analysis_markdown = analyze_financial_report(
            extracted_pdf_text=extracted_pdf_text,
            api_market_data_json=api_market_data_json,
            openai_api_key=application_config.openai_api_key,
            openai_model=application_config.openai_model,
            api_context_markdown=api_context_with_per_markdown,
        )
        guarded_analysis_markdown = guard_ai_analysis_markdown(
            analysis_markdown=ai_analysis_markdown,
            period_check_result=period_check_result,
        )

        print("投資判断支援セクションを作成しています...")
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

        print("Markdownレポートを保存しています...")
        saved_report_path = save_markdown_report(
            markdown_text=full_report_markdown,
            source_pdf_path=pdf_file_path,
            output_directory=report_output_directory,
        )

        print("")
        print("分析レポートの作成が完了しました。")
        print(f"保存先: {saved_report_path}")

    except FileNotFoundError as error:
        print("")
        print("ファイルが見つかりませんでした。")
        print(f"詳細: {error}")
        print("PDFのパスが正しいか、data/pdfs フォルダにPDFを置いたか確認してください。")
        sys.exit(1)

    except ValueError as error:
        print("")
        print("設定または入力内容に問題があります。")
        print(f"詳細: {error}")
        print(".envの内容、PDFファイル、インストール済みライブラリを確認してください。")
        sys.exit(1)

    except Exception as error:
        print("")
        print("予期しないエラーが発生しました。")
        print(f"詳細: {error}")
        print("まずはPDFファイル、OPENAI_API_KEY、インターネット接続を確認してください。")
        sys.exit(1)


# この処理の役割:
# python main.py ... と実行されたときだけ、アプリ本体を開始します。
if __name__ == "__main__":
    run_application()
