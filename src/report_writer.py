# このファイルの役割:
# AIが作成した分析結果をMarkdownファイルとして保存します。

from datetime import datetime
from pathlib import Path


# この関数の役割:
# レポート保存用のファイル名を作ります。
# なぜ必要か:
# 元のPDF名と作成日時を入れることで、どのPDFの分析結果か後から分かりやすくするためです。
def create_report_file_name(source_pdf_path: Path) -> str:
    # Discord Bot化すると、複数ユーザーが同時にPDFを送る可能性があります。
    # 秒単位だけだと同じファイル名になることがあるため、マイクロ秒まで含めます。
    current_time_text = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    pdf_file_name_without_extension = source_pdf_path.stem

    return f"{pdf_file_name_without_extension}_analysis_{current_time_text}.md"


# この関数の役割:
# Markdownテキストを指定フォルダに保存し、保存したファイルのパスを返します。
def save_markdown_report(
    markdown_text: str,
    source_pdf_path: Path,
    output_directory: Path,
) -> Path:
    if markdown_text.strip() == "":
        raise ValueError("保存するMarkdownテキストが空です。")

    # 保存先フォルダが存在しない場合は自動で作ります。
    # これにより、初回実行時でも手作業でフォルダを作る必要がありません。
    output_directory.mkdir(parents=True, exist_ok=True)

    report_file_name = create_report_file_name(source_pdf_path)
    report_file_path = output_directory / report_file_name

    report_file_path.write_text(markdown_text, encoding="utf-8")

    return report_file_path
