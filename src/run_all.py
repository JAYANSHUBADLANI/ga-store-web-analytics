"""Run the whole pipeline: load -> KPI queries and figures -> Excel workbook -> deck -> README."""
import json

import analysis
import deck
import excel_dashboard
import load
import render_readme

if __name__ == "__main__":
    stats = load.build()
    results = analysis.main(stats)
    print("workbook:", excel_dashboard.build())
    print("deck:", deck.build())
    print("readme:", render_readme.render())
    print(json.dumps({"customer_conversion_rate": results["customers"]["conversion_rate"]}, indent=2))
