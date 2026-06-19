# このファイルの役割:
# CLIアプリの入り口です。引数と設定を読み込み、共通のレポート生成サービスを呼び出します。
#
# なぜ必要か:
# レポート生成の中心処理はsrc/report_service.pyに分け、
# 将来のDiscord Botからも同じ処理を呼び出せるようにするためです。

import argparse
import sys

from src.config import load_application_config
from src.report_service import generate_report


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
# CLI向けに途中経過を表示します。
def print_progress(message: str) -> None:
    print(message)


# この関数の役割:
# CLIとしてアプリを実行します。
def run_application() -> None:
    argument_parser = create_argument_parser()
    command_line_arguments = argument_parser.parse_args()

    ticker = command_line_arguments.ticker or command_line_arguments.stock_code or ""

    try:
        print("設定を読み込んでいます...")
        application_config = load_application_config()

        generation_result = generate_report(
            pdf_path=command_line_arguments.pdf_path,
            output_dir=command_line_arguments.output_dir,
            openai_api_key=application_config.openai_api_key,
            openai_model=application_config.openai_model,
            jquants_api_key=application_config.jquants_api_key,
            stock_code=command_line_arguments.stock_code,
            ticker=ticker,
            period_type=command_line_arguments.period_type,
            fiscal_year_end=command_line_arguments.fiscal_year_end,
            progress_callback=print_progress,
        )

        print("")
        print(generation_result.message)
        print(f"保存先: {generation_result.report_file_path}")

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
