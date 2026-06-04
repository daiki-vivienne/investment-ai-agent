# このファイルの役割:
# アプリ全体の入り口です。PDFを読み込み、AIで分析し、Markdownレポートとして保存します。

from pathlib import Path
import argparse
import sys

from src.ai_analyzer import analyze_financial_report
from src.config import load_application_config
from src.pdf_reader import extract_text_from_pdf
from src.report_writer import save_markdown_report


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

        print("AIに分析を依頼しています。少し時間がかかる場合があります...")
        analysis_markdown = analyze_financial_report(
            extracted_pdf_text=extracted_pdf_text,
            openai_api_key=application_config.openai_api_key,
            openai_model=application_config.openai_model,
        )

        print("Markdownレポートを保存しています...")
        saved_report_path = save_markdown_report(
            markdown_text=analysis_markdown,
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
