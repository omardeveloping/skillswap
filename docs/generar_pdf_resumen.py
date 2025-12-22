"""Genera docs/backend_resumen.pdf a partir de docs/backend_resumen.md sin dependencias externas."""
from pathlib import Path
import textwrap

BASE_DIR = Path(__file__).resolve().parent
MD_PATH = BASE_DIR / "backend_resumen.md"
PDF_PATH = BASE_DIR / "backend_resumen.pdf"

PAGE_WIDTH = 612  # 8.5in * 72
PAGE_HEIGHT = 792  # 11in * 72
LEFT_MARGIN = 72
TOP_START = 760
BOTTOM_MARGIN = 60
LINE_HEIGHT = 14
WRAP_WIDTH = 95


def escape_pdf_text(text: str) -> str:
    return text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def markdown_to_lines(md_text: str) -> list[str]:
    lines: list[str] = []
    for raw in md_text.splitlines():
        if not raw.strip():
            lines.append("")
            continue
        if raw.startswith("### "):
            line = raw[4:].strip().upper()
        elif raw.startswith("## "):
            line = raw[3:].strip().upper()
        elif raw.startswith("# "):
            continue  # se omite el título principal; va en el header del PDF
        elif raw.startswith("- "):
            line = f"• {raw[2:].strip()}"
        else:
            line = raw.strip()
        wrapped = textwrap.wrap(line, width=WRAP_WIDTH) or [""]
        lines.extend(wrapped)
    return lines


def paginate(lines: list[str]) -> list[list[str]]:
    pages: list[list[str]] = []
    current: list[str] = []
    y = TOP_START
    for line in lines:
        if y < BOTTOM_MARGIN:
            pages.append(current)
            current = []
            y = TOP_START
        current.append(line)
        y -= LINE_HEIGHT
    if current:
        pages.append(current)
    return pages


def build_content_stream(lines: list[str]) -> str:
    parts = [
        "BT",
        "/F1 12 Tf",
        f"{LINE_HEIGHT} TL",
        f"{LEFT_MARGIN} {TOP_START} Td",
    ]
    first = True
    for line in lines:
        if first:
            first = False
        else:
            parts.append("T*")
        if line == "":
            parts.append("T*")
            continue
        parts.append(f"({escape_pdf_text(line)}) Tj")
    parts.append("ET")
    return "\n".join(parts) + "\n"


def build_pdf_objects(pages: list[list[str]]):
    objects = [None, None, None]  # índices 1 y 2 reservados para catálogo/páginas

    font_obj = "<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>"
    objects.append(font_obj)  # objeto 3
    font_num = len(objects) - 1

    page_numbers: list[int] = []

    for page_lines in pages:
        stream = build_content_stream(page_lines)
        content_obj = f"<< /Length {len(stream.encode('utf-8'))} >>\nstream\n{stream}endstream"
        objects.append(content_obj)
        content_num = len(objects) - 1

        page_obj = (
            "<< /Type /Page /Parent 2 0 R "
            f"/MediaBox [0 0 {PAGE_WIDTH} {PAGE_HEIGHT}] "
            f"/Resources << /Font << /F1 {font_num} 0 R >> >> "
            f"/Contents {content_num} 0 R >>"
        )
        objects.append(page_obj)
        page_numbers.append(len(objects) - 1)

    pages_obj = (
        "<< /Type /Pages "
        f"/Kids [{' '.join(f'{n} 0 R' for n in page_numbers)}] "
        f"/Count {len(page_numbers)} >>"
    )
    objects[2] = pages_obj

    catalog_obj = "<< /Type /Catalog /Pages 2 0 R >>"
    objects[1] = catalog_obj

    return objects


def write_pdf(objects: list[str], output_path: Path):
    output = ["%PDF-1.4\n"]
    offsets = [0]  # offset para el objeto 0 (null)

    for idx in range(1, len(objects)):
        obj_str = objects[idx]
        if obj_str is None:
            raise ValueError(f"Objeto {idx} sin definir")
        offset = sum(len(part.encode("utf-8")) for part in output)
        offsets.append(offset)
        output.append(f"{idx} 0 obj\n{obj_str}\nendobj\n")

    xref_offset = sum(len(part.encode("utf-8")) for part in output)
    output.append(f"xref\n0 {len(objects)}\n")
    output.append("0000000000 65535 f \n")
    for off in offsets[1:]:
        output.append(f"{off:010} 00000 n \n")
    output.append(
        "trailer\n"
        f"<< /Size {len(objects)} /Root 1 0 R >>\n"
        "startxref\n"
        f"{xref_offset}\n"
        "%%EOF\n"
    )

    output_path.write_bytes("".join(output).encode("utf-8"))


def main():
    markdown_text = MD_PATH.read_text(encoding="utf-8")
    lines = markdown_to_lines(markdown_text)
    pages = paginate(lines)
    objects = build_pdf_objects(pages)
    write_pdf(objects, PDF_PATH)
    print(f"PDF generado en {PDF_PATH}")


if __name__ == "__main__":
    main()
