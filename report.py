from __future__ import annotations

from pathlib import Path
from uuid import uuid4

import pandas as pd
from openpyxl import load_workbook
from openpyxl.styles import Alignment, Font, PatternFill


def write_daily_report(
    output_path: Path,
    holdings: pd.DataFrame,
    category: pd.DataFrame,
    market: pd.DataFrame,
    data_quality: pd.DataFrame,
    advice: list[str],
    errors: pd.DataFrame,
) -> None:
    temp_path = output_path.with_name(f"{output_path.stem}.tmp-{uuid4().hex}{output_path.suffix}")

    with pd.ExcelWriter(temp_path, engine="openpyxl") as writer:
        holdings.to_excel(writer, sheet_name="Holdings", index=False)
        category.to_excel(writer, sheet_name="Category", index=False)
        market.to_excel(writer, sheet_name="Market", index=False)
        data_quality.to_excel(writer, sheet_name="DataQuality", index=False)
        pd.DataFrame({"advice": advice}).to_excel(writer, sheet_name="Advice", index=False)
        errors.to_excel(writer, sheet_name="Errors", index=False)
    format_workbook(temp_path)

    try:
        temp_path.replace(output_path)
    except PermissionError as exc:
        temp_path.unlink(missing_ok=True)
        raise PermissionError("daily_report.xlsx 可能正在被 Excel 打开，请关闭后重新运行。") from exc


def format_workbook(path: Path) -> None:
    workbook = load_workbook(path)
    header_fill = PatternFill("solid", fgColor="D9EAF7")
    header_font = Font(bold=True)
    percent_headers = {"current_weight", "proxy_return_pct", "return_pct", "target_weight", "deviation", "drawdown_from_high"}
    money_headers = {
        "initial_amount",
        "accumulated_auto_invest",
        "current_amount",
        "estimated_daily_pnl",
        "previous_close",
        "latest_close",
        "value",
        "us10y_change",
    }
    widths = {
        "Holdings": {"A": 42, "B": 16, "C": 22, "D": 16, "E": 10, "F": 20, "G": 16, "H": 18, "I": 20},
        "Category": {"A": 20, "B": 16, "C": 16, "D": 16, "E": 16},
        "Market": {"A": 10, "B": 14, "C": 16, "D": 14, "E": 14, "F": 18, "G": 14, "H": 14, "I": 12, "J": 14, "K": 40},
        "DataQuality": {"A": 10, "B": 14, "C": 16, "D": 14, "E": 44},
        "Advice": {"A": 110},
        "Errors": {"A": 90},
    }

    for sheet_name in workbook.sheetnames:
        sheet = workbook[sheet_name]
        sheet.freeze_panes = "A2"

        for cell in sheet[1]:
            cell.fill = header_fill
            cell.font = header_font
            cell.alignment = Alignment(horizontal="center")

        for column_letter, width in widths.get(sheet_name, {}).items():
            sheet.column_dimensions[column_letter].width = width

        for row in sheet.iter_rows(min_row=2):
            for cell in row:
                cell.alignment = Alignment(vertical="top", wrap_text=True)
                header = sheet.cell(row=1, column=cell.column).value
                if header in percent_headers and isinstance(cell.value, (int, float)):
                    cell.number_format = "0.00%"
                elif header in money_headers and isinstance(cell.value, (int, float)):
                    cell.number_format = "0.00"

    workbook.save(path)
