# このファイルの役割:
# 決算PDFファイルからテキストを取り出します。

from pathlib import Path


# この関数の役割:
# 指定されたPDFファイルを開き、全ページのテキストを1つの文字列として返します。
# なぜ必要か:
# AIはPDFそのものではなく、基本的にはテキストを入力として受け取るためです。
def extract_text_from_pdf(pdf_file_path: Path) -> str:
    try:
        from pypdf import PdfReader
    except ModuleNotFoundError:
        raise ValueError("pypdfがインストールされていません。pip install -r requirements.txt を実行してください。")

    if not pdf_file_path.exists():
        raise FileNotFoundError(f"{pdf_file_path} が存在しません。")

    if not pdf_file_path.is_file():
        raise ValueError(f"{pdf_file_path} はファイルではありません。")

    if pdf_file_path.suffix.lower() != ".pdf":
        raise ValueError("PDFファイルを指定してください。拡張子が .pdf のファイルが必要です。")

    try:
        pdf_reader = PdfReader(str(pdf_file_path))
    except Exception as error:
        error_message = str(error)

        # AES方式で保護されたPDFは、pypdfだけでは読めない場合があります。
        # cryptographyを入れると、暗号化PDFを開くために必要な処理が使えるようになります。
        if "cryptography" in error_message and "AES" in error_message:
            raise ValueError(
                "このPDFを読むには cryptography という追加ライブラリが必要です。"
                "pip install -r requirements.txt をもう一度実行してください。"
            )

        raise ValueError(f"PDFを開けませんでした。ファイルが壊れていないか確認してください: {error}")

    extracted_text_by_page: list[str] = []

    for page_index, pdf_page in enumerate(pdf_reader.pages, start=1):
        page_text = pdf_page.extract_text()

        # PDFによっては画像だけで作られていて、テキストを取り出せないページがあります。
        # Noneの場合は空文字にしておくと、後続処理でエラーになりにくくなります。
        if page_text is None:
            page_text = ""

        extracted_text_by_page.append(f"\n--- ページ {page_index} ---\n{page_text}")

    extracted_text = "\n".join(extracted_text_by_page).strip()

    if extracted_text == "":
        raise ValueError(
            "PDFからテキストを抽出できませんでした。画像だけのPDFの場合は、OCR処理が必要です。"
        )

    return extracted_text
