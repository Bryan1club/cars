# export_db.py -- turns club.py's live SQLite database (club.db, pulled off
# a board's SD card) into the data files the MMBasic pages read.
# Run with: python mmbasic/export_db.py path/to/club.db [table ...]
#
# Same format as export_workbook.py: one record per line, "|" between
# fields, in club.py's column order. Tables default to members and cars;
# events/attend/finance only when named (the live database may have none
# while the workbook has the sample ones).

import os
import sqlite3
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "data")
TABLES = {
    "members": ("members.dat", "number,name,email,phone,status,financial,role,notes,visited,logbook,address", "number"),
    "cars": ("cars.dat", "id,member,descr,rego,logbook", "id"),
    "events": ("events.dat", "key,name,date,time,place,notes", "key"),
    "attend": ("attend.dat", "evkey,member,time", "evkey"),
    "finance": ("finance.dat", "id,date,descr,category,kind,amount,notes", "id"),
}


def cell(v):
    if v is None:
        return ""
    if isinstance(v, float) and v.is_integer():
        v = int(v)
    return str(v).replace("|", "/").replace("\r", " ").replace("\n", " ").strip()


def main():
    db = sqlite3.connect(sys.argv[1])
    wanted = sys.argv[2:] or ["members", "cars"]
    os.makedirs(OUT, exist_ok=True)
    for t in wanted:
        fname, cols, order = TABLES[t]
        rows = db.execute("SELECT %s FROM %s ORDER BY %s" % (cols, t, order)).fetchall()
        if t == "members":
            # the 98 generated test members (numbers 1000+, all
            # @example.com) stay out -- the owner: "leave those 100 out"
            rows = [r for r in rows if not (r[2] or "").lower().endswith("@example.com")]
        with open(os.path.join(OUT, fname), "w", newline="\r\n") as f:
            f.write("".join("|".join(cell(v) for v in r) + "\n" for r in rows))
        print("%-12s %4d records" % (fname, len(rows)))


if __name__ == "__main__":
    main()
