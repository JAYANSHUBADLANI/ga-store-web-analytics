"""Run the KPI queries, add the statistics, save tables, figures and results.json."""
import json
import re
from pathlib import Path

import duckdb
import matplotlib
import numpy as np
import pandas as pd
from scipy import stats

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
PARQUET = ROOT / "data" / "processed" / "sessions.parquet"
SQL = ROOT / "sql" / "kpis.sql"
TABLES = ROOT / "reports" / "tables"
FIGS = ROOT / "reports" / "figures"

BLUE, GREY, ORANGE, DARK = "#1f5fa8", "#b8bec6", "#e07b24", "#2b2b2b"


def load_queries(path: Path = SQL) -> dict:
    """Split the SQL file into {name: query} on '-- name:' markers."""
    text = path.read_text()
    blocks = re.split(r"^-- name:\s*(\w+)\s*$", text, flags=re.M)
    return {blocks[i]: blocks[i + 1].strip().rstrip(";") for i in range(1, len(blocks), 2)}


def wilson(successes, n, z=1.96):
    """95% Wilson interval for a proportion (works for small counts too)."""
    successes, n = np.asarray(successes, float), np.asarray(n, float)
    p = successes / n
    denom = 1 + z**2 / n
    centre = (p + z**2 / (2 * n)) / denom
    half = z * np.sqrt(p * (1 - p) / n + z**2 / (4 * n**2)) / denom
    return centre - half, centre + half


def two_prop_z(x1, n1, x2, n2):
    p1, p2 = x1 / n1, x2 / n2
    p = (x1 + x2) / (n1 + n2)
    se = np.sqrt(p * (1 - p) * (1 / n1 + 1 / n2))
    z = (p1 - p2) / se
    return float(z), float(2 * stats.norm.sf(abs(z)))


def run(con) -> dict:
    out = {}
    for name, q in load_queries().items():
        df = con.execute(q).df()
        if {"conversions", "sessions"} <= set(df.columns) and "conversion_rate" in df.columns:
            lo, hi = wilson(df["conversions"], df["sessions"])
            df["cr_low"], df["cr_high"] = lo, hi
        df.to_csv(TABLES / f"{name}.csv", index=False)
        out[name] = df
    return out


def style(ax, title):
    ax.set_title(title, loc="left", fontsize=12, color=DARK, fontweight="bold")
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    ax.tick_params(colors=DARK)


def figures(t: dict) -> None:
    ch = t["by_channel"]
    # 1. session share vs revenue share by channel
    fig, ax = plt.subplots(figsize=(9, 4.6))
    x = np.arange(len(ch))
    ax.bar(x - 0.2, ch["session_share"] * 100, 0.4, color=GREY, label="Share of sessions")
    ax.bar(x + 0.2, ch["revenue_share"] * 100, 0.4, color=BLUE, label="Share of revenue")
    ax.set_xticks(x, ch["channel"], rotation=20, ha="right")
    ax.set_ylabel("% of customer total")
    ax.legend(frameon=False)
    style(ax, "Traffic and revenue do not come from the same channels")
    fig.tight_layout(); fig.savefig(FIGS / "channel_traffic_vs_revenue.png", dpi=160); plt.close(fig)

    # 2. conversion rate by channel with 95% CI
    c = ch[ch["sessions"] >= 1000].sort_values("conversion_rate")
    fig, ax = plt.subplots(figsize=(9, 4.6))
    err = np.vstack([(c["conversion_rate"] - c["cr_low"]) * 100, (c["cr_high"] - c["conversion_rate"]) * 100])
    ax.barh(c["channel"], c["conversion_rate"] * 100, xerr=err, color=BLUE, ecolor=DARK, capsize=3)
    for i, v in enumerate(c["conversion_rate"] * 100):
        ax.text(v + 0.08, i, f"{v:.2f}%", va="center", fontsize=9, color=DARK)
    ax.set_xlabel("Conversion rate (% of sessions with a purchase), 95% interval")
    style(ax, "Conversion rate by channel (customer traffic)")
    fig.tight_layout(); fig.savefig(FIGS / "conversion_by_channel.png", dpi=160); plt.close(fig)

    # 3. device
    dv = t["by_device"]
    fig, axes = plt.subplots(1, 2, figsize=(9, 4))
    axes[0].bar(dv["device"], dv["session_share"] * 100, color=GREY)
    axes[0].bar(dv["device"], dv["revenue_share"] * 100, color=BLUE, width=0.45)
    axes[0].set_ylabel("%"); style(axes[0], "Sessions (grey) vs revenue (blue)")
    axes[1].bar(dv["device"], dv["conversion_rate"] * 100, color=[BLUE if d == "desktop" else ORANGE for d in dv["device"]])
    for i, v in enumerate(dv["conversion_rate"] * 100):
        axes[1].text(i, v + 0.02, f"{v:.2f}%", ha="center", fontsize=9)
    axes[1].set_ylabel("Conversion rate %"); style(axes[1], "Conversion rate by device")
    fig.tight_layout(); fig.savefig(FIGS / "device.png", dpi=160); plt.close(fig)

    # 4. funnel
    fu = t["funnel"]
    fig, ax = plt.subplots(figsize=(9, 4.2))
    ax.barh(fu["stage"][::-1], fu["sessions"][::-1], color=[BLUE] * 4 + [ORANGE])
    for i, (s, v) in enumerate(zip(fu["stage"][::-1], fu["sessions"][::-1])):
        ax.text(v, i, f"  {v:,.0f} ({v / fu['sessions'].iloc[0] * 100:.1f}%)", va="center", fontsize=9)
    ax.set_xlim(0, fu["sessions"].iloc[0] * 1.25)
    ax.set_xlabel("Customer sessions")
    style(ax, "Engagement funnel: where sessions drop out")
    fig.tight_layout(); fig.savefig(FIGS / "funnel.png", dpi=160); plt.close(fig)

    # 5. monthly sessions, social highlighted, revenue line
    mo = t["monthly"]
    fig, ax = plt.subplots(figsize=(9, 4.6))
    other = mo["customer_sessions"] - mo["social_sessions"]
    ax.bar(mo["month"], other / 1000, color=GREY, label="Other customer sessions")
    ax.bar(mo["month"], mo["social_sessions"] / 1000, bottom=other / 1000, color=ORANGE, label="Social sessions")
    ax.set_ylabel("Sessions (thousands)")
    ax2 = ax.twinx()
    ax2.plot(mo["month"], mo["customer_revenue"] / 1000, color=BLUE, marker="o", label="Customer revenue")
    ax2.set_ylabel("Revenue ($ thousands)", color=BLUE)
    ax2.set_ylim(0, mo["customer_revenue"].max() / 1000 * 1.15)
    ax2.spines["top"].set_visible(False)
    ax.set_xticks(range(len(mo)), mo["month"], rotation=45, ha="right")
    h1, l1 = ax.get_legend_handles_labels(); h2, l2 = ax2.get_legend_handles_labels()
    ax.legend(h1 + h2, l1 + l2, frameon=False, loc="upper left", fontsize=8)
    style(ax, "Autumn 2016 traffic spike was social, and revenue did not follow")
    fig.tight_layout(); fig.savefig(FIGS / "monthly_trend.png", dpi=160); plt.close(fig)

    # 6. depth bands
    db = t["depth_bands"]
    fig, ax = plt.subplots(figsize=(9, 4))
    ax.bar(db["depth"], db["conversion_rate"] * 100, color=BLUE)
    for i, (v, s) in enumerate(zip(db["conversion_rate"] * 100, db["session_share"] * 100)):
        ax.text(i, v + 0.5, f"{v:.1f}% CR\n{s:.0f}% of sessions", ha="center", fontsize=8)
    ax.set_ylabel("Conversion rate %")
    ax.set_ylim(0, db["conversion_rate"].max() * 100 * 1.25)
    style(ax, "Conversion climbs steeply with pages viewed")
    fig.tight_layout(); fig.savefig(FIGS / "depth_conversion.png", dpi=160); plt.close(fig)

    # 7. internal vs customers
    hl = t["headline"].set_index("segment")
    seg = ["Customers (external)", "Internal (googleplex.com)"]
    tot = hl.loc["All traffic"]
    shares = pd.DataFrame({
        "Sessions": [hl.loc[s, "sessions"] / tot["sessions"] * 100 for s in seg],
        "Purchases": [hl.loc[s, "conversions"] / tot["conversions"] * 100 for s in seg],
        "Revenue": [hl.loc[s, "revenue"] / tot["revenue"] * 100 for s in seg],
    }, index=["Customers", "Internal (googleplex.com)"])
    fig, ax = plt.subplots(figsize=(9, 3.6))
    left = np.zeros(3)
    for name, colr in zip(shares.index, [GREY, BLUE]):
        ax.barh(shares.columns, shares.loc[name], left=left, color=colr, label=name)
        for i, v in enumerate(shares.loc[name]):
            ax.text(left[i] + v / 2, i, f"{v:.1f}%", ha="center", va="center", fontsize=9,
                    color="white" if colr == BLUE else DARK)
        left += shares.loc[name].values
    ax.legend(frameon=False, loc="upper center", bbox_to_anchor=(0.5, -0.12), ncol=2, fontsize=8)
    ax.set_xlim(0, 100)
    style(ax, "Internal network traffic inflates every headline KPI")
    fig.tight_layout(); fig.savefig(FIGS / "internal_share.png", dpi=160); plt.close(fig)


def summarise(t: dict, load_stats: dict) -> dict:
    hl = t["headline"].set_index("segment")
    allt, cust, intl = hl.loc["All traffic"], hl.loc["Customers (external)"], hl.loc["Internal (googleplex.com)"]
    dv = t["by_device"].set_index("device")
    z, p = two_prop_z(dv.loc["desktop", "conversions"], dv.loc["desktop", "sessions"],
                      dv.loc["mobile", "conversions"], dv.loc["mobile", "sessions"])
    cd = t["channel_device"].pivot(index="channel", columns="device", values="conversion_rate")
    cd_c = t["channel_device"].pivot(index="channel", columns="device", values="conversions")
    # only compare channels with enough purchases on both devices to read a rate
    ok = (cd_c["desktop"] >= 50) & (cd_c["mobile"] >= 50)
    ratio = (cd["desktop"] / cd["mobile"])[ok]
    ch = t["by_channel"].set_index("channel")
    mo = t["monthly"].set_index("month")
    soc = t["social_sources"].set_index("source")
    vt = t["visitor_type"].set_index("visitor_type")
    db = t["depth_bands"].set_index("depth")
    fu = t["funnel"].set_index("stage")
    peak = mo["social_sessions"].idxmax()
    late = mo.loc["2017-05":"2017-07", "social_sessions"].mean()
    r = {
        "data": {**load_stats, "months_in_trend": len(mo)},
        "all_traffic": {k: float(allt[k]) for k in ["sessions", "visitors", "conversions", "conversion_rate", "revenue", "bounce_rate", "pages_per_session", "revenue_per_order"]},
        "customers": {k: float(cust[k]) for k in ["sessions", "visitors", "conversions", "conversion_rate", "revenue", "bounce_rate", "pages_per_session", "revenue_per_session", "revenue_per_order"]},
        "internal": {
            "sessions": float(intl["sessions"]), "conversion_rate": float(intl["conversion_rate"]),
            "session_share": float(intl["sessions"] / allt["sessions"]),
            "conversion_share": float(intl["conversions"] / allt["conversions"]),
            "revenue_share": float(intl["revenue"] / allt["revenue"]),
            "cr_multiple_vs_customers": float(intl["conversion_rate"] / cust["conversion_rate"]),
        },
        "channels": {c: {k: float(ch.loc[c, k]) for k in ["sessions", "session_share", "bounce_rate", "pages_per_session", "conversion_rate", "revenue_share", "revenue_per_session"]} for c in ch.index},
        "device": {
            d: {k: float(dv.loc[d, k]) for k in ["sessions", "session_share", "conversion_rate", "revenue_share", "bounce_rate", "pages_per_session"]} for d in dv.index},
        "device_test": {"desktop_vs_mobile_cr_ratio": float(dv.loc["desktop", "conversion_rate"] / dv.loc["mobile", "conversion_rate"]), "z": z, "p_value": p,
                         "within_channel_ratio_min": float(ratio.min()), "within_channel_ratio_max": float(ratio.max()),
                         "within_channel_channels": list(ratio.index)},
        "visitor_type": {v: {k: float(vt.loc[v, k]) for k in ["sessions", "session_share", "conversion_rate", "revenue_share"]} for v in vt.index},
        "depth": {d: {k: float(db.loc[d, k]) for k in ["session_share", "conversion_rate", "conversion_share"]} for d in db.index},
        "funnel": {s: float(fu.loc[s, "sessions"]) for s in fu.index},
        "social": {
            "peak_month": pd.Timestamp(peak + "-01").strftime("%B %Y"), "peak_sessions": float(mo.loc[peak, "social_sessions"]),
            "may_jul_2017_avg": float(late),
            "youtube_share_of_social": float(soc.loc["youtube.com", "sessions"] / t["by_channel"].set_index("channel").loc["Social", "sessions"]),
            "youtube_conversions": float(soc.loc["youtube.com", "conversions"]),
            "youtube_sessions": float(soc.loc["youtube.com", "sessions"]),
        },
        "top_country": {
            "us_session_share": float(t["top_countries"].set_index("country").loc["United States", "sessions"] / cust["sessions"]),
            "us_revenue_share": float(t["top_countries"].set_index("country").loc["United States", "revenue_share"]),
        },
    }
    return r


def order_stats(con) -> dict:
    q = con.execute("""
        SELECT quantile_cont(revenue_usd, 0.5), quantile_cont(revenue_usd, 0.9), MAX(revenue_usd), COUNT(*),
               SUM(CASE WHEN pageviews >= 10 THEN 1 ELSE 0 END)
        FROM customers WHERE converted = 1""").fetchone()
    disp = con.execute("""
        SELECT SUM(revenue_usd), MAX(revenue_usd), SUM(CASE WHEN source = 'dfa' THEN revenue_usd ELSE 0 END)
        FROM customers WHERE channel = 'Display'""").fetchone()
    return {"median_order": q[0], "p90_order": q[1], "largest_order": q[2], "orders": q[3],
            "orders_with_10plus_pages_share": q[4] / q[3],
            "display_revenue": disp[0], "display_largest_order_share": disp[1] / disp[0],
            "display_dfa_share": disp[2] / disp[0]}


def main(load_stats: dict) -> dict:
    TABLES.mkdir(parents=True, exist_ok=True); FIGS.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect()
    con.execute(f"CREATE VIEW sessions AS SELECT * FROM '{PARQUET}'")
    con.execute("CREATE VIEW customers AS SELECT * FROM sessions WHERE is_internal = 0")
    t = run(con)
    figures(t)
    r = summarise(t, load_stats)
    r["orders"] = order_stats(con)
    (ROOT / "reports" / "results.json").write_text(json.dumps(r, indent=2, default=float))
    return r


if __name__ == "__main__":
    from load import build
    print(json.dumps(main(build()), indent=2, default=float))
