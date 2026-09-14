"""แปลง รายการอะไหล่อู่ซ่อมรถ.xlsx เป็น seed/parts.csv — อ่าน xlsx ด้วย stdlib ไม่ต้องลง openpyxl

รันใหม่ทุกครั้งที่ไฟล์ Excel เปลี่ยน  python backend/scripts/xlsx_to_seed.py
"""

import csv
import re
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET

NS = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
REL = "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}"

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "รายการอะไหล่อู่ซ่อมรถ.xlsx"
TARGET = ROOT / "backend" / "seed" / "parts.csv"

# ชื่อชีตคือประเภทรถในตัวมันเอง ชีตสรุปเป็นคำอธิบายไฟล์ ไม่ใช่ข้อมูล
APPLIES_TO = {"ใช้ร่วมกัน": "both", "รถยนต์": "car", "มอเตอร์ไซค์": "motorcycle"}
HEADER_ROWS = 3
CATEGORY, NAME, BRAND, SPEC, UNIT, PRICE = "B", "C", "D", "E", "F", "G"


def read_sheets(path: Path) -> dict[str, list[dict[str, str]]]:
    with zipfile.ZipFile(path) as book:
        shared = [
            "".join(node.text or "" for node in item.iter(NS + "t"))
            for item in ET.fromstring(book.read("xl/sharedStrings.xml"))
        ]
        targets = {
            rel.get("Id"): rel.get("Target").lstrip("/")
            for rel in ET.fromstring(book.read("xl/_rels/workbook.xml.rels"))
        }
        sheets = {}
        for sheet in ET.fromstring(book.read("xl/workbook.xml")).find(NS + "sheets"):
            target = targets[sheet.get(REL + "id")]
            source = book.read(target if target.startswith("xl/") else "xl/" + target)
            sheets[sheet.get("name")] = read_rows(ET.fromstring(source), shared)
    return sheets


def read_rows(worksheet: ET.Element, shared: list[str]) -> list[dict[str, str]]:
    rows = []
    for row in worksheet.iter(NS + "row"):
        cells = {}
        for cell in row.iter(NS + "c"):
            value = cell.find(NS + "v")
            if cell.get("t") == "inlineStr":
                text = "".join(node.text or "" for node in cell.iter(NS + "t"))
            elif value is None:
                continue
            else:
                text = shared[int(value.text)] if cell.get("t") == "s" else value.text
            cells[re.match(r"[A-Z]+", cell.get("r")).group()] = text.strip()
        rows.append(cells)
    return rows


def resolve_applies_to(category: str, sheet_default: str) -> str:
    """ชีต 'ใช้ร่วมกัน' มีหมวดน้ำมันเครื่องที่ระบุประเภทรถไว้ในชื่อหมวดเอง ชื่อหมวดชนะชีต

    น้ำมันเครื่องมอเตอร์ไซค์ 4T เติมรถยนต์ไม่ได้ ถ้าปล่อยเป็น both จะโผล่ผิดตัวกรอง 50 รายการ
    """
    if "มอเตอร์ไซค์" in category:
        return "motorcycle"
    if "รถยนต์" in category:
        return "car"
    return sheet_default


def build_name(row: dict[str, str]) -> str:
    """ต่อสเปคท้ายชื่อ ไม่แยกเป็นคอลัมน์ เพราะมีของที่ชื่อซ้ำกันแล้วต่างกันแค่ขนาด"""
    name, spec = row[NAME], row.get(SPEC, "")
    return f"{name} {spec}" if spec and spec not in name else name


def collect(sheets: dict[str, list[dict[str, str]]]) -> list[dict[str, str]]:
    parts = []
    for sheet_name, applies_to in APPLIES_TO.items():
        for row in sheets[sheet_name][HEADER_ROWS:]:
            if not row.get(NAME):
                continue
            parts.append(
                {
                    "category": row[CATEGORY],
                    "name": build_name(row),
                    "brand": row.get(BRAND, ""),
                    "unit": row.get(UNIT, ""),
                    "sale_price": row[PRICE],
                    "applies_to": resolve_applies_to(row[CATEGORY], applies_to),
                }
            )
    return parts


def main() -> None:
    parts = collect(read_sheets(SOURCE))

    names = [part["name"] for part in parts]
    assert len(parts) == 503, f"คาดว่า 503 รายการ ได้ {len(parts)}"
    assert len(set(names)) == len(names), "ชื่อสินค้าซ้ำ ต้องแยกด้วยสเปคให้ได้ก่อน"
    assert all(float(part["sale_price"]) > 0 for part in parts), "มีราคาที่ไม่เป็นบวก"
    assert all(part["category"] and part["unit"] for part in parts), "หมวดหมู่หรือหน่วยว่าง"

    TARGET.parent.mkdir(exist_ok=True)
    with TARGET.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(parts[0]))
        writer.writeheader()
        writer.writerows(parts)

    print(f"{TARGET.relative_to(ROOT)}  {len(parts)} รายการ  {len({p['category'] for p in parts})} หมวดหมู่")


if __name__ == "__main__":
    main()
