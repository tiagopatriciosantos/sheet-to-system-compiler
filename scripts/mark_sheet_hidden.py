"""Mark one exported XLSX sheet hidden when the spreadsheet facade has no visibility API.

The workbook itself is authored and exported by @oai/artifact-tool. This narrow
metadata-only interoperability step changes only the `state` attribute in
xl/workbook.xml so the demo can preserve the hidden-sheet business signal.
"""

from __future__ import annotations

import sys
import tempfile
import zipfile
from pathlib import Path
from xml.etree import ElementTree


MAIN_NS = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
NS = {"main": MAIN_NS}


def mark_hidden(path: Path, sheet_name: str) -> None:
    with zipfile.ZipFile(path, "r") as source:
        workbook_xml = ElementTree.fromstring(source.read("xl/workbook.xml"))
        target = next(
            (sheet for sheet in workbook_xml.findall("main:sheets/main:sheet", NS) if sheet.attrib.get("name") == sheet_name),
            None,
        )
        if target is None:
            raise ValueError(f"Sheet not found: {sheet_name}")
        target.set("state", "hidden")
        updated_xml = ElementTree.tostring(workbook_xml, encoding="utf-8", xml_declaration=True)

        with tempfile.NamedTemporaryFile(dir=path.parent, suffix=".xlsx", delete=False) as temporary:
            temporary_path = Path(temporary.name)
        try:
            with zipfile.ZipFile(temporary_path, "w") as destination:
                for item in source.infolist():
                    payload = updated_xml if item.filename == "xl/workbook.xml" else source.read(item.filename)
                    destination.writestr(item, payload)
            path.write_bytes(temporary_path.read_bytes())
        finally:
            temporary_path.unlink(missing_ok=True)


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("Usage: mark_sheet_hidden.py <workbook.xlsx>")
    mark_hidden(Path(sys.argv[1]), "Config")
