# export_workbook.py -- turns club_data_workbook.xlsx into the data files
# the MMBasic pages read: members.dat, cars.dat, events.dat, finance.dat.
# Run with: python mmbasic/export_workbook.py
#
# One record per line, fields separated by "|" (addresses have commas),
# in the workbook's column order, header row dropped. "|" and line breaks
# inside a value are replaced so a record always stays on one line.

import os
import datetime
import openpyxl

HERE = os.path.dirname(os.path.abspath(__file__))
BOOK = os.path.join(HERE, "..", "club_data_workbook.xlsx")
OUT = os.path.join(HERE, "data")
SHEETS = {"Members": ("members.dat", 11), "Cars": ("cars.dat", 5),
          "Events": ("events.dat", 6), "Financial": ("finance.dat", 7)}


def cell(v):
    if v is None:
        return ""
    if isinstance(v, datetime.datetime):
        v = v.date()
    if isinstance(v, float) and v.is_integer():
        v = int(v)
    return str(v).replace("|", "/").replace("\r", " ").replace("\n", " ").strip()


def main():
    os.makedirs(OUT, exist_ok=True)
    wb = openpyxl.load_workbook(BOOK, read_only=True, data_only=True)
    for sheet, (fname, ncols) in SHEETS.items():
        rows = list(wb[sheet].iter_rows(values_only=True))[1:]
        lines = []
        for r in rows:
            vals = [cell(v) for v in r[:ncols]]
            # skip notes and blank rows: members/cars/finance need a number
            # in the first column, events a date (their key)
            if not vals[0] or not vals[0].replace("-", "").isdigit():
                continue
            lines.append("|".join(vals))
        with open(os.path.join(OUT, fname), "w", newline="\r\n") as f:
            f.write("\n".join(lines) + "\n")
        print("%-12s %3d records" % (fname, len(lines)))


if __name__ == "__main__":
    main()
