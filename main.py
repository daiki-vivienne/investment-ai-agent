# このファイルの役割:
# アプリ全体の入り口です。PDFを読み込み、AIで分析し、Markdownレポートとして保存します。

from pathlib import Path
import argparse
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
from src.pdf_reader import extract_text_from_pdf
from src.report_writer import save_markdown_report
from src.valuation_analyzer import calculate_per_analysis


# この関数の役割:
# コマンドラインから受け取る引数を定義します。
# なぜ必要か:
# 将来、株価取得やニュース取得などのオプションを増やすときも、ここを拡張すれば分かりやすいためです。
def create_argument_parser() -> argparse.ArgumentParser:
    argument_parser = argparse.ArgumentParser(
        description="決算PDFをAIで分析し、Markdownレポートを作成します。"
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

    return argument_parser


# この関数の役割:
# 実際の処理を順番に実行します。
# PDF読み込み → AI分析 → Markdown保存、というアプリの中心になる流れです。
def run_application() -> None:
    argument_parser = create_argument_parser()
    command_line_arguments = argument_parser.parse_args()

    pdf_file_path = Path(command_line_arguments.pdf_path)
    report_output_directory = Path(command_line_arguments.output_dir)

    try:
        print("設定を読み込んでいます...")
        application_config = load_application_config()

        print(f"PDFを読み込んでいます: {pdf_file_path}")
        extracted_pdf_text = extract_text_from_pdf(pdf_file_path)

        print("J-Quants APIデータの期間整合性を確認しています...")
        period_check_result = check_jquants_period_consistency(
            api_key=application_config.jquants_api_key,
            stock_code=command_line_arguments.stock_code,
            period_type=command_line_arguments.period_type,
            fiscal_year_end=command_line_arguments.fiscal_year_end,
        )
        api_context_markdown = build_api_context_for_ai(period_check_result)
        period_consistency_markdown = build_period_consistency_markdown(period_check_result)
        formal_performance_summary_markdown = build_formal_performance_summary_markdown(period_check_result)

        print("PER分析を確認しています...")
        per_analysis_result = calculate_per_analysis(
            stock_code=command_line_arguments.stock_code,
            period_check_result=period_check_result,
        )
        per_analysis_markdown = build_per_analysis_markdown(per_analysis_result)
        api_context_with_per_markdown = f"{api_context_markdown}\n\nPER分析:\n{per_analysis_markdown}"

        print("AIに分析を依頼しています。少し時間がかかる場合があります...")
        analysis_markdown = analyze_financial_report(
            extracted_pdf_text=extracted_pdf_text,
            openai_api_key=application_config.openai_api_key,
            openai_model=application_config.openai_model,
            api_context_markdown=api_context_with_per_markdown,
        )
        guarded_analysis_markdown = guard_ai_analysis_markdown(
            analysis_markdown=analysis_markdown,
            period_check_result=period_check_result,
        )
        full_report_markdown = (
            f"{period_consistency_markdown}\n\n"
            f"{formal_performance_summary_markdown}\n\n"
            f"{per_analysis_markdown}\n\n"
            f"---\n\n"
            f"{guarded_analysis_markdown}"
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
        print(".envの内容やPDFファイルの中身を確認してください。")
        sys.exit(1)

    except Exception as error:
        print("")
        print("予期しないエラーが発生しました。")
        print(f"詳細: {error}")
        print("まずはPDFファイル、OPENAI_API_KEY、インターネット接続を確認してください。")
        sys.exit(1)


# この処理の役割:
# python main.py ... と実行されたときだけ、アプリ本体を開始します。
# なぜ必要か:
# 将来テストコードからmain.pyを読み込んでも、自動で実行されないようにするためです。
if __name__ == "__main__":
    run_application()
