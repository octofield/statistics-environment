"""把講義 PDF 的文字抽出成 .txt，讓 VS Code 的全資料夾搜尋（Ctrl+Shift+F）可以搜到講義內容。

    python tools/extract_pdf_text.py <PDF 資料夾> [輸出資料夾]
"""
import sys
from pathlib import Path

from pypdf import PdfReader


def extract(pdf, out_dir):
    reader = PdfReader(pdf)
    pages = []
    for i, page in enumerate(reader.pages, 1):
        text = (page.extract_text() or "").strip()
        pages.append(f"===== {pdf.name} p.{i} =====\n{text}\n")
    out = out_dir / (pdf.stem + ".txt")
    out.write_text("\n".join(pages), encoding="utf-8")
    return out, len(reader.pages)


if __name__ == "__main__":
    src = Path(sys.argv[1])
    dst = Path(sys.argv[2]) if len(sys.argv) > 2 else src / "_text"
    dst.mkdir(parents=True, exist_ok=True)
    for pdf in sorted(src.glob("*.pdf")):
        try:
            out, n = extract(pdf, dst)
            print(f"{pdf.name}: {n} 頁 → {out.name}")
        except Exception as e:
            print(f"{pdf.name}: 失敗 {e}")
