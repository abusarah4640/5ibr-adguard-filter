#!/usr/bin/env python3

import csv
import html as html_utils
from pathlib import Path

from scripts.cli import parse_no_args

ROOT = Path(__file__).resolve().parent.parent

REPORTS = ROOT / "reports"

INPUT = REPORTS / "new_candidates.csv"
OUTPUT = REPORTS / "report.html"


def load_rows():

    if not INPUT.exists():
        return []

    with open(INPUT, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def build_html(rows):

    html = """<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<title>5ibr Dashboard</title>

<style>

body{
    font-family:Arial,sans-serif;
    background:#f4f4f4;
    margin:40px;
}

h1{
    color:#222;
}

table{
    width:100%;
    border-collapse:collapse;
    background:white;
}

th,td{
    border:1px solid #ddd;
    padding:8px;
}

th{
    background:#333;
    color:white;
}

tr:nth-child(even){
    background:#f9f9f9;
}

.badge{
    padding:4px 8px;
    border-radius:5px;
    background:#007acc;
    color:white;
}

</style>

</head>

<body>

<h1>5ibr Query Analysis Dashboard</h1>

<p>Total Suggestions: <strong>%TOTAL%</strong></p>

<table>

<tr>
<th>Requests</th>
<th>Vendor</th>
<th>Category</th>
<th>Confidence</th>
<th>Domain</th>
<th>Suggested Rule</th>
</tr>

"""

    for row in rows:

        requests = html_utils.escape(row["Requests"])
        vendor = html_utils.escape(row["Vendor"])
        category = html_utils.escape(row["Category"])
        confidence = html_utils.escape(row["Confidence"])
        domain = html_utils.escape(row["Domain"])
        suggested_rule = html_utils.escape(row["Suggested Rule"])

        html += f"""
<tr>

<td>{requests}</td>

<td>{vendor}</td>

<td><span class="badge">{category}</span></td>

<td>{confidence}%</td>

<td>{domain}</td>

<td><code>{suggested_rule}</code></td>

</tr>
"""

    html += """
</table>

</body>

</html>
"""

    html = html.replace("%TOTAL%", str(len(rows)))

    return html


def main(argv: list[str] | None = None) -> int:
    """Generate an HTML report from query-log analysis candidates."""

    parse_no_args(
        prog="fivebr html-report",
        description="Generate an HTML report",
        argv=argv,
    )

    rows = load_rows()

    OUTPUT.write_text(
        build_html(rows),
        encoding="utf-8"
    )

    print()
    print("=================================")
    print("5ibr HTML Dashboard")
    print("=================================")
    print()
    print(f"Generated : {OUTPUT}")
    print()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
