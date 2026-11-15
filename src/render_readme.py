"""Write README.md from reports/README_template.md and reports/results.json."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def p(x, d=1):
    return f"{x * 100:.{d}f}%"


def render() -> Path:
    r = json.loads((ROOT / "reports" / "results.json").read_text())
    A, C, I, ch, dv, dt = r["all_traffic"], r["customers"], r["internal"], r["channels"], r["device"], r["device_test"]
    vt, so, od, d, db, fu = r["visitor_type"], r["social"], r["orders"], r["data"], r["depth"], r["funnel"]
    rows = "\n".join(
        f"| {c} | {v['sessions']:,.0f} | {p(v['session_share'])} | {p(v['bounce_rate'])} | {v['pages_per_session']:.2f} | "
        f"{p(v['conversion_rate'], 2)} | {p(v['revenue_share'])} | ${v['revenue_per_session']:.2f} |"
        for c, v in ch.items() if c != "(Other)")
    dev = "\n".join(
        f"| {k} | {v['sessions']:,.0f} | {p(v['session_share'])} | {p(v['bounce_rate'])} | {v['pages_per_session']:.2f} | "
        f"{p(v['conversion_rate'], 2)} | {p(v['revenue_share'])} |" for k, v in dv.items())
    depth = "\n".join(f"| {k} | {p(v['session_share'])} | {p(v['conversion_rate'], 2)} | {p(v['conversion_share'])} |" for k, v in db.items())
    vals = {
        "raw_rows": f"{d['raw_rows']:,}", "raw_columns": d["raw_columns"], "kept_columns": d["kept_columns"],
        "visitors_all": f"{A['visitors']:,.0f}", "dups": d["duplicate_session_id_rows"], "missing_pv": d["sessions_missing_pageviews"],
        "a_sessions": f"{A['sessions']:,.0f}", "c_sessions": f"{C['sessions']:,.0f}", "i_sessions": f"{I['sessions']:,.0f}",
        "a_conv": f"{A['conversions']:,.0f}", "c_conv": f"{C['conversions']:,.0f}", "i_conv": f"{A['conversions'] - C['conversions']:,.0f}",
        "a_cr": p(A["conversion_rate"], 2), "c_cr": p(C["conversion_rate"], 2), "i_cr": p(I["conversion_rate"], 2),
        "a_rev": f"${A['revenue']:,.0f}", "c_rev": f"${C['revenue']:,.0f}", "i_rev": f"${A['revenue'] - C['revenue']:,.0f}",
        "a_bounce": p(A["bounce_rate"]), "c_bounce": p(C["bounce_rate"]), "a_pps": f"{A['pages_per_session']:.2f}", "c_pps": f"{C['pages_per_session']:.2f}",
        "i_sess_share": p(I["session_share"]), "i_conv_share": p(I["conversion_share"]), "i_rev_share": p(I["revenue_share"]),
        "i_mult": f"{I['cr_multiple_vs_customers']:.0f}", "channel_rows": rows, "device_rows": dev, "depth_rows": depth,
        "ratio": f"{dt['desktop_vs_mobile_cr_ratio']:.1f}", "z": f"{dt['z']:.1f}",
        "wc_min": f"{dt['within_channel_ratio_min']:.1f}", "wc_max": f"{dt['within_channel_ratio_max']:.1f}",
        "wc_channels": ", ".join(dt["within_channel_channels"]),
        "soc_peak": f"{so['peak_sessions']:,.0f}", "soc_peak_month": so["peak_month"], "soc_late": f"{so['may_jul_2017_avg']:,.0f}",
        "yt_share": p(so["youtube_share_of_social"]), "yt_sess": f"{so['youtube_sessions']:,.0f}", "yt_conv": f"{so['youtube_conversions']:.0f}",
        "soc_sess_share": p(ch["Social"]["session_share"]), "soc_rev_share": p(ch["Social"]["revenue_share"]), "soc_bounce": p(ch["Social"]["bounce_rate"]),
        "ret_sess": p(vt["Returning"]["session_share"]), "ret_rev": p(vt["Returning"]["revenue_share"]),
        "ret_cr": p(vt["Returning"]["conversion_rate"], 2), "new_cr": p(vt["New"]["conversion_rate"], 2),
        "ret_mult": f"{vt['Returning']['conversion_rate'] / vt['New']['conversion_rate']:.1f}",
        "median_order": f"${od['median_order']:,.2f}", "p90_order": f"${od['p90_order']:,.2f}", "max_order": f"${od['largest_order']:,.2f}",
        "deep_share": p(od["orders_with_10plus_pages_share"]), "disp_top": p(od["display_largest_order_share"]), "disp_dfa": p(od["display_dfa_share"]),
        "f_sess": f"{fu['Sessions']:,.0f}", "f_eng": f"{fu['Engaged (2+ pages, no bounce)']:,.0f}", "f_browse": f"{fu['Browsed (5+ pages)']:,.0f}",
        "f_deep": f"{fu['Deep (10+ pages)']:,.0f}", "f_buy": f"{fu['Purchased']:,.0f}",
        "one_page": p(db["1 page"]["session_share"]),
        "us_sess": p(r["top_country"]["us_session_share"]), "us_rev": p(r["top_country"]["us_revenue_share"]),
        "mob_sess": p(dv["mobile"]["session_share"]), "mob_rev": p(dv["mobile"]["revenue_share"]),
        "ps_cr": p(ch["Paid Search"]["conversion_rate"], 2), "ps_share": p(ch["Paid Search"]["session_share"]),
        "dir_share": p(ch["Direct"]["session_share"]), "dir_rev": p(ch["Direct"]["revenue_share"]),
    }
    text = (ROOT / "reports" / "README_template.md").read_text()
    for k, v in vals.items():
        text = text.replace("{{" + k + "}}", str(v))
    assert "{{" not in text, text[text.index("{{"): text.index("{{") + 40]
    out = ROOT / "README.md"
    out.write_text(text)
    return out


if __name__ == "__main__":
    print(render())
