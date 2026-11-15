"""Build the Excel KPI workbook: a dashboard sheet plus one sheet per breakdown.

Every rate in the workbook is an Excel formula over raw counts (sessions, bounces,
pageviews, purchases, revenue), so a reviewer can click any cell and see how it
was calculated. Charts are native Excel charts, not pasted images.
"""
from pathlib import Path

import duckdb
from openpyxl import Workbook
from openpyxl.chart import BarChart, LineChart, Reference
from openpyxl.formatting.rule import DataBarRule
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter

ROOT = Path(__file__).resolve().parents[1]
PARQUET = ROOT / "data" / "processed" / "sessions.parquet"
OUT = ROOT / "reports" / "GA_Store_KPI_Dashboard.xlsx"

NAVY, LIGHT, WHITE = "1F3B5C", "EAF0F7", "FFFFFF"
HEAD_FONT = Font(bold=True, color=WHITE)
HEAD_FILL = PatternFill("solid", fgColor=NAVY)
THIN = Side(style="thin", color="C9D3DF")
BOX = Border(left=THIN, right=THIN, top=THIN, bottom=THIN)

COUNTS = """
SELECT {dim} AS {label}, COUNT(*) AS sessions, SUM(bounced) AS bounces, SUM(pageviews) AS pageviews,
       SUM(converted) AS purchases, ROUND(SUM(revenue_usd), 2) AS revenue
FROM customers {where} GROUP BY 1 ORDER BY {order}
"""

# derived columns written as formulas; {r} is the row number
DERIVED = [
    ("Share of sessions", "=B{r}/SUM(B${first}:B${last})", "0.0%"),
    ("Bounce rate", "=C{r}/B{r}", "0.0%"),
    ("Pages / session", "=D{r}/B{r}", "0.00"),
    ("Conversion rate", "=E{r}/B{r}", "0.00%"),
    ("Revenue / session", "=F{r}/B{r}", '"$"#,##0.00'),
    ("Revenue / order", '=IF(E{r}=0,"",F{r}/E{r})', '"$"#,##0.00'),
    ("Share of revenue", "=F{r}/SUM(F${first}:F${last})", "0.0%"),
]


def header(ws, row, cols):
    for j, c in enumerate(cols, 1):
        cell = ws.cell(row=row, column=j, value=c)
        cell.font, cell.fill, cell.border = HEAD_FONT, HEAD_FILL, BOX
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
    ws.row_dimensions[row].height = 32


def breakdown_sheet(wb, con, title, dim, label, where="", order="sessions DESC", note=""):
    ws = wb.create_sheet(title)
    ws["A1"] = title
    ws["A1"].font = Font(bold=True, size=14, color=NAVY)
    ws["A2"] = note or "Customer traffic only (internal googleplex.com sessions excluded)."
    ws["A2"].font = Font(italic=True, color="666666")
    rows = con.execute(COUNTS.format(dim=dim, label=label, where=where, order=order)).fetchall()
    cols = [label.replace("_", " ").title(), "Sessions", "Bounces", "Pageviews", "Purchases", "Revenue ($)"] + [d[0] for d in DERIVED]
    header(ws, 4, cols)
    first, last = 5, 4 + len(rows)
    for i, row in enumerate(rows):
        r = first + i
        for j, v in enumerate(row, 1):
            c = ws.cell(row=r, column=j, value=v)
            c.border = BOX
            if j in (2, 3, 4, 5):
                c.number_format = "#,##0"
            if j == 6:
                c.number_format = '"$"#,##0'
        for k, (_, f, fmt) in enumerate(DERIVED):
            c = ws.cell(row=r, column=7 + k, value=f.format(r=r, first=first, last=last))
            c.number_format, c.border = fmt, BOX
        if i % 2:
            for j in range(1, len(cols) + 1):
                ws.cell(row=r, column=j).fill = PatternFill("solid", fgColor=LIGHT)
    tot = last + 1
    ws.cell(row=tot, column=1, value="Total").font = Font(bold=True)
    for j in range(2, 7):
        L = get_column_letter(j)
        c = ws.cell(row=tot, column=j, value=f"=SUM({L}{first}:{L}{last})")
        c.font, c.number_format, c.border = Font(bold=True), ('"$"#,##0' if j == 6 else "#,##0"), BOX
    for k, (_, f, fmt) in enumerate(DERIVED):
        if "SUM" in f:
            continue
        c = ws.cell(row=tot, column=7 + k, value=f.format(r=tot, first=first, last=last))
        c.number_format, c.font, c.border = fmt, Font(bold=True), BOX
    cr_col = get_column_letter(7 + [d[0] for d in DERIVED].index("Conversion rate"))
    ws.conditional_formatting.add(f"{cr_col}{first}:{cr_col}{last}", DataBarRule(start_type="min", end_type="max", color="5B8FD0"))
    ws.column_dimensions["A"].width = 26
    for j in range(2, len(cols) + 1):
        ws.column_dimensions[get_column_letter(j)].width = 13
    ws.freeze_panes = "B5"
    ws.auto_filter.ref = f"A4:{get_column_letter(len(cols))}{last}"
    return ws, first, last


def build() -> Path:
    con = duckdb.connect()
    con.execute(f"CREATE VIEW sessions AS SELECT * FROM '{PARQUET}'")
    con.execute("CREATE VIEW customers AS SELECT * FROM sessions WHERE is_internal = 0")
    wb = Workbook()
    dash = wb.active
    dash.title = "Dashboard"

    ch, c1, cl = breakdown_sheet(wb, con, "Channels", "channel", "channel")
    dv, d1, dl = breakdown_sheet(wb, con, "Devices", "device", "device")
    breakdown_sheet(wb, con, "Visitor type", "CASE WHEN visit_number = 1 THEN 'New' ELSE 'Returning' END", "visitor_type")
    breakdown_sheet(wb, con, "Countries", "country", "country", order="sessions DESC LIMIT 15",
                    note="Top 15 countries by customer sessions. Shares are of these 15 countries.")
    mo, m1, ml = breakdown_sheet(wb, con, "Monthly", "strftime(session_date, '%Y-%m')", "month",
                                 where="WHERE session_date < DATE '2017-08-01'", order="1",
                                 note="Aug 2016 to Jul 2017 (the export ends with one partial day, 1 Aug 2017, left out).")
    breakdown_sheet(wb, con, "Traffic source", "source || ' / ' || medium", "source_medium",
                    order="sessions DESC LIMIT 20", note="Top 20 source / medium pairs. Shares are of these 20.")
    # Dashboard sheet
    dash["A1"] = "Google Merchandise Store: Website KPI Dashboard"
    dash["A1"].font = Font(bold=True, size=16, color=NAVY)
    dash["A2"] = "Customer sessions, Aug 2016 to Aug 2017. Every tile is a formula over the Channels sheet totals."
    dash["A2"].font = Font(italic=True, color="666666")
    tot = cl + 1
    tiles = [
        ("Sessions", f"=Channels!B{tot}", "#,##0"),
        ("Purchases", f"=Channels!E{tot}", "#,##0"),
        ("Conversion rate", f"=Channels!E{tot}/Channels!B{tot}", "0.00%"),
        ("Revenue", f"=Channels!F{tot}", '"$"#,##0'),
        ("Revenue / session", f"=Channels!F{tot}/Channels!B{tot}", '"$"#,##0.00'),
        ("Bounce rate", f"=Channels!C{tot}/Channels!B{tot}", "0.0%"),
        ("Pages / session", f"=Channels!D{tot}/Channels!B{tot}", "0.00"),
        ("Mobile conversion vs desktop", "=INDEX(Devices!J5:J7,MATCH(\"mobile\",Devices!A5:A7,0))/INDEX(Devices!J5:J7,MATCH(\"desktop\",Devices!A5:A7,0))", "0.00\"x\""),
    ]
    for i, (name, f, fmt) in enumerate(tiles):
        col = 1 + (i % 4) * 2
        row = 4 + (i // 4) * 3
        a = dash.cell(row=row, column=col, value=name)
        a.font, a.fill = Font(bold=True, color=WHITE, size=9), HEAD_FILL
        b = dash.cell(row=row + 1, column=col, value=f)
        b.font, b.number_format, b.fill = Font(bold=True, size=16, color=NAVY), fmt, PatternFill("solid", fgColor=LIGHT)
        dash.merge_cells(start_row=row, start_column=col, end_row=row, end_column=col + 1)
        dash.merge_cells(start_row=row + 1, start_column=col, end_row=row + 1, end_column=col + 1)
    for j in range(1, 9):
        dash.column_dimensions[get_column_letter(j)].width = 14

    bar = BarChart(); bar.type = "bar"; bar.title = "Conversion rate by channel"; bar.style = 10
    bar.add_data(Reference(ch, min_col=10, min_row=4, max_row=cl), titles_from_data=True)
    bar.set_categories(Reference(ch, min_col=1, min_row=c1, max_row=cl))
    bar.y_axis.numFmt = "0.0%"; bar.height, bar.width = 7.5, 15; bar.legend = None
    dash.add_chart(bar, "A11")

    share = BarChart(); share.title = "Share of sessions vs share of revenue"; share.style = 10
    share.add_data(Reference(ch, min_col=7, min_row=4, max_row=cl), titles_from_data=True)
    share.add_data(Reference(ch, min_col=13, min_row=4, max_row=cl), titles_from_data=True)
    share.set_categories(Reference(ch, min_col=1, min_row=c1, max_row=cl))
    share.y_axis.numFmt = "0%"; share.height, share.width = 7.5, 15
    dash.add_chart(share, "J11")

    line = LineChart(); line.title = "Monthly customer sessions"; line.style = 12
    line.add_data(Reference(mo, min_col=2, min_row=4, max_row=ml), titles_from_data=True)
    line.set_categories(Reference(mo, min_col=1, min_row=m1, max_row=ml))
    line.height, line.width = 7.5, 15; line.legend = None
    dash.add_chart(line, "A27")

    dbar = BarChart(); dbar.title = "Conversion rate by device"; dbar.style = 10
    dbar.add_data(Reference(dv, min_col=10, min_row=4, max_row=dl), titles_from_data=True)
    dbar.set_categories(Reference(dv, min_col=1, min_row=d1, max_row=dl))
    dbar.y_axis.numFmt = "0.0%"; dbar.height, dbar.width = 7.5, 15; dbar.legend = None
    dash.add_chart(dbar, "J27")

    defs = wb.create_sheet("Definitions")
    rows = [("KPI", "Definition"),
            ("Session", "One visit as recorded by Google Analytics. A visit that crosses midnight is split into two sessions (898 such pairs)."),
            ("Bounce", "A session with a single interaction (GA's totals.bounces = 1)."),
            ("Purchase / conversion", "A session with transaction revenue above zero. The export has no order count, so one converting session = one order."),
            ("Conversion rate", "Purchases / sessions."),
            ("Revenue", "GA transactionRevenue divided by 1,000,000 (GA stores it in micro-units), in US dollars."),
            ("Revenue / session", "Revenue / sessions: what an average visit is worth."),
            ("Customers", "All sessions except those referred from googleplex.com, Google's internal network."),
            ("Source", "Kaggle 'Google Analytics Customer Revenue Prediction' training export (903,653 sessions, 55 fields).")]
    for i, (a, b) in enumerate(rows, 1):
        defs.cell(row=i, column=1, value=a).font = Font(bold=(i == 1))
        defs.cell(row=i, column=2, value=b)
    header(defs, 1, ["KPI", "Definition"])
    defs.column_dimensions["A"].width, defs.column_dimensions["B"].width = 24, 110

    # this one sheet compares internal with customer traffic, so it reads all sessions
    con.execute("CREATE OR REPLACE VIEW customers AS SELECT * FROM sessions")
    breakdown_sheet(wb, con, "Internal vs customers",
                    "CASE WHEN is_internal = 1 THEN 'Internal (googleplex.com)' ELSE 'Customers' END", "segment",
                    note="All sessions, split into Google's internal network traffic and outside customers.")
    wb.move_sheet("Definitions", offset=len(wb.sheetnames))
    wb.properties.creator = wb.properties.lastModifiedBy = "Jayanshu Badlani"
    wb.properties.title = OUT.stem.replace("_", " ")
    OUT.parent.mkdir(parents=True, exist_ok=True)
    wb.save(OUT)
    return OUT


if __name__ == "__main__":
    print(build())
