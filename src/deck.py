"""Build the stakeholder deck (reports/GA_Store_Insights.pptx) from results.json and the figures.

Slide titles state the finding; the body gives the numbers behind it. Two charts are
native PowerPoint charts so they can be restyled or updated in PowerPoint.
"""
import json
from pathlib import Path

from pptx import Presentation
from pptx.chart.data import CategoryChartData
from pptx.dml.color import RGBColor
from pptx.enum.chart import XL_CHART_TYPE, XL_LEGEND_POSITION
from pptx.enum.text import PP_ALIGN
from pptx.util import Inches, Pt

ROOT = Path(__file__).resolve().parents[1]
FIGS = ROOT / "reports" / "figures"
OUT = ROOT / "reports" / "GA_Store_Insights.pptx"
NAVY, GREY, BLUE, ORANGE = RGBColor(0x1F, 0x3B, 0x5C), RGBColor(0x55, 0x5B, 0x63), RGBColor(0x1F, 0x5F, 0xA8), RGBColor(0xE0, 0x7B, 0x24)


def pct(x, d=1):
    return f"{x * 100:.{d}f}%"


def add_title(slide, text, sub=None):
    tb = slide.shapes.add_textbox(Inches(0.5), Inches(0.3), Inches(12.3), Inches(0.9))
    p = tb.text_frame.paragraphs[0]
    p.text, p.font.size, p.font.bold, p.font.color.rgb = text, Pt(24), True, NAVY
    tb.text_frame.word_wrap = True
    if sub:
        s = slide.shapes.add_textbox(Inches(0.5), Inches(1.05), Inches(12.3), Inches(0.4))
        q = s.text_frame.paragraphs[0]
        q.text, q.font.size, q.font.color.rgb = sub, Pt(13), GREY
    line = slide.shapes.add_connector(1, Inches(0.5), Inches(1.5), Inches(12.83), Inches(1.5))
    line.line.color.rgb, line.line.width = NAVY, Pt(1.5)


def bullets(slide, items, left, top, width, height, size=14):
    tb = slide.shapes.add_textbox(left, top, width, height)
    tf = tb.text_frame
    tf.word_wrap = True
    for i, it in enumerate(items):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.text = "• " + it
        p.font.size, p.font.color.rgb = Pt(size), RGBColor(0x2B, 0x2B, 0x2B)
        p.space_after = Pt(10)
    return tb


def footer(slide, n):
    tb = slide.shapes.add_textbox(Inches(0.5), Inches(7.05), Inches(12.3), Inches(0.3))
    p = tb.text_frame.paragraphs[0]
    p.text = f"Google Merchandise Store, GA session export Aug 2016 to Aug 2017  |  {n}"
    p.font.size, p.font.color.rgb = Pt(9), GREY


def picture_slide(prs, title, sub, fig, items, n):
    s = prs.slides.add_slide(prs.slide_layouts[6])
    add_title(s, title, sub)
    s.shapes.add_picture(str(FIGS / fig), Inches(0.5), Inches(1.75), width=Inches(7.6))
    bullets(s, items, Inches(8.4), Inches(1.8), Inches(4.4), Inches(5))
    footer(s, n)
    return s


def build() -> Path:
    r = json.loads((ROOT / "reports" / "results.json").read_text())
    A, C, I, ch, dv = r["all_traffic"], r["customers"], r["internal"], r["channels"], r["device"]
    vt, so, od, dt = r["visitor_type"], r["social"], r["orders"], r["device_test"]
    prs = Presentation()
    prs.slide_width, prs.slide_height = Inches(13.333), Inches(7.5)

    # 1. title
    s = prs.slides.add_slide(prs.slide_layouts[6])
    bg = s.shapes.add_shape(1, 0, 0, prs.slide_width, prs.slide_height)
    bg.fill.solid(); bg.fill.fore_color.rgb = NAVY; bg.line.fill.background()
    tb = s.shapes.add_textbox(Inches(0.8), Inches(2.4), Inches(11.5), Inches(2.5))
    tf = tb.text_frame; tf.word_wrap = True
    p = tf.paragraphs[0]; p.text = "Google Merchandise Store: website performance review"
    p.font.size, p.font.bold, p.font.color.rgb = Pt(36), True, RGBColor(0xFF, 0xFF, 0xFF)
    p = tf.add_paragraph()
    p.text = (f"{A['sessions']:,.0f} sessions, {A['visitors']:,.0f} visitors, Aug 2016 to Aug 2017. "
              "Where traffic comes from, where it converts, and what to change.")
    p.font.size, p.font.color.rgb = Pt(16), RGBColor(0xD6, 0xE2, 0xF0)

    # 2. executive summary
    s = prs.slides.add_slide(prs.slide_layouts[6])
    add_title(s, "Summary: real customer conversion is 0.76%, and mobile and social are where it leaks")
    bullets(s, [
        f"Google's internal network is {pct(I['session_share'])} of sessions but {pct(I['conversion_share'])} of purchases. "
        f"Removing it, customer conversion is {pct(C['conversion_rate'], 2)}, not the {pct(A['conversion_rate'], 2)} the unfiltered report shows.",
        f"Mobile is {pct(dv['mobile']['session_share'])} of customer sessions but {pct(dv['mobile']['revenue_share'])} of revenue. "
        f"Mobile visitors browse as much as desktop visitors, but desktop converts {dt['desktop_vs_mobile_cr_ratio']:.1f}x as often.",
        f"Social brought {pct(ch['Social']['session_share'])} of sessions and {pct(ch['Social']['revenue_share'])} of revenue; "
        f"YouTube alone sent {so['youtube_sessions']:,.0f} sessions and {so['youtube_conversions']:.0f} purchases.",
        f"Returning visitors are {pct(vt['Returning']['session_share'])} of sessions and {pct(vt['Returning']['revenue_share'])} of revenue, "
        f"converting at {pct(vt['Returning']['conversion_rate'], 2)} against {pct(vt['New']['conversion_rate'], 2)} for new visitors.",
        "Recommended: filter internal traffic, test a simpler mobile checkout, judge social on engagement not sessions, and invest in bringing visitors back.",
    ], Inches(0.5), Inches(1.8), Inches(12.3), Inches(5), size=16)
    footer(s, 2)

    # 3. KPI snapshot (native table)
    s = prs.slides.add_slide(prs.slide_layouts[6])
    add_title(s, "KPI snapshot: internal network traffic distorts every headline number",
              "Same KPIs computed three ways. Customer traffic is the basis for the rest of this deck.")
    rows = [("KPI", "All traffic", "Customers", "Internal (googleplex.com)")]
    hl = {"All traffic": A, "Customers": C}
    rows += [("Sessions", f"{A['sessions']:,.0f}", f"{C['sessions']:,.0f}", f"{I['sessions']:,.0f}"),
             ("Purchases", f"{A['conversions']:,.0f}", f"{C['conversions']:,.0f}", f"{A['conversions'] - C['conversions']:,.0f}"),
             ("Conversion rate", pct(A['conversion_rate'], 2), pct(C['conversion_rate'], 2), pct(I['conversion_rate'], 2)),
             ("Revenue", f"${A['revenue']:,.0f}", f"${C['revenue']:,.0f}", f"${A['revenue'] - C['revenue']:,.0f}"),
             ("Bounce rate", pct(A['bounce_rate']), pct(C['bounce_rate']), "-"),
             ("Pages per session", f"{A['pages_per_session']:.2f}", f"{C['pages_per_session']:.2f}", "-"),
             ("Median order value (customers)", "-", f"${od['median_order']:,.2f}", "-")]
    tbl = s.shapes.add_table(len(rows), 4, Inches(0.5), Inches(1.8), Inches(12.3), Inches(4.2)).table
    for i, row in enumerate(rows):
        for j, v in enumerate(row):
            cell = tbl.cell(i, j); cell.text = v
            para = cell.text_frame.paragraphs[0]
            para.font.size, para.font.bold = Pt(14), (i == 0 or j == 0)
            if j:
                para.alignment = PP_ALIGN.CENTER
    footer(s, 3)

    picture_slide(prs, "40% of revenue comes through Google's internal network, not outside customers",
                  "Sessions referred from googleplex.com, the company's internal network",
                  "internal_share.png", [
                      f"Internal sessions convert at {pct(I['conversion_rate'], 2)}, {I['cr_multiple_vs_customers']:.0f}x the customer rate.",
                      f"Left in, they lift the store's conversion rate from {pct(C['conversion_rate'], 2)} to {pct(A['conversion_rate'], 2)} and hide how outside visitors behave.",
                      "Action: add a GA view or segment that excludes googleplex.com referrals, and report customers and staff separately.",
                  ], 4)

    picture_slide(prs, "Direct and organic search earn the revenue; social and affiliates bring empty traffic",
                  "Customer sessions by GA default channel grouping", "channel_traffic_vs_revenue.png", [
                      f"Direct: {pct(ch['Direct']['session_share'])} of sessions, {pct(ch['Direct']['revenue_share'])} of revenue, ${ch['Direct']['revenue_per_session']:.2f} per session.",
                      f"Organic search: {pct(ch['Organic Search']['session_share'])} of sessions, {pct(ch['Organic Search']['revenue_share'])} of revenue.",
                      f"Paid search converts at {pct(ch['Paid Search']['conversion_rate'], 2)} on only {pct(ch['Paid Search']['session_share'])} of sessions: the best candidate to scale.",
                      f"Display shows ${ch['Display']['revenue_per_session']:.2f} per session, but one order is {pct(od['display_largest_order_share'])} of its revenue. Too thin to act on yet.",
                  ], 5)

    picture_slide(prs, "The autumn 2016 traffic spike was YouTube, and it did not sell",
                  "Monthly customer sessions with social highlighted, and customer revenue", "monthly_trend.png", [
                      f"Social sessions peaked at {so['peak_sessions']:,.0f} in {so['peak_month']} and averaged {so['may_jul_2017_avg']:,.0f} a month in May to Jul 2017.",
                      f"YouTube was {pct(so['youtube_share_of_social'])} of social sessions: {so['youtube_sessions']:,.0f} sessions, {so['youtube_conversions']:.0f} purchases.",
                      f"Social sessions bounce {pct(ch['Social']['bounce_rate'])} of the time and view {ch['Social']['pages_per_session']:.1f} pages.",
                      "Action: report social against engagement and assisted-conversion goals, not raw sessions, so a spike like this is not read as growth.",
                  ], 6)

    picture_slide(prs, f"Same browsing, but desktop buys {dt['desktop_vs_mobile_cr_ratio']:.1f}x as often as mobile",
                  "Customer sessions by device", "device.png", [
                      f"Pages per session: {dv['mobile']['pages_per_session']:.2f} mobile vs {dv['desktop']['pages_per_session']:.2f} desktop. Bounce: {pct(dv['mobile']['bounce_rate'])} vs {pct(dv['desktop']['bounce_rate'])}.",
                      f"Conversion: {pct(dv['mobile']['conversion_rate'], 2)} mobile vs {pct(dv['desktop']['conversion_rate'], 2)} desktop (two-proportion z = {dt['z']:.1f}).",
                      f"The gap holds inside each large channel ({', '.join(dt['within_channel_channels'])}): desktop converts {dt['within_channel_ratio_min']:.1f}x to {dt['within_channel_ratio_max']:.1f}x better, so it is not a channel mix effect.",
                      "Interest is there; buying is not. That points at the mobile cart and checkout. Action: A/B test a shorter mobile checkout.",
                  ], 7)

    # 8. new vs returning: native chart
    s = prs.slides.add_slide(prs.slide_layouts[6])
    add_title(s, "One visit in five is a return visit, and it brings three quarters of revenue",
              "New vs returning customer sessions")
    cd = CategoryChartData()
    cd.categories = ["Share of sessions", "Share of revenue"]
    cd.add_series("New", (vt["New"]["session_share"], vt["New"]["revenue_share"]))
    cd.add_series("Returning", (vt["Returning"]["session_share"], vt["Returning"]["revenue_share"]))
    gf = s.shapes.add_chart(XL_CHART_TYPE.COLUMN_STACKED_100, Inches(0.5), Inches(1.8), Inches(7.6), Inches(4.9), cd)
    chart = gf.chart
    chart.has_legend, chart.legend.position, chart.legend.include_in_layout = True, XL_LEGEND_POSITION.BOTTOM, False
    plot = chart.plots[0]; plot.has_data_labels = True
    plot.data_labels.number_format, plot.data_labels.number_format_is_linked = "0%", False
    plot.series[0].format.fill.solid(); plot.series[0].format.fill.fore_color.rgb = RGBColor(0xB8, 0xBE, 0xC6)
    plot.series[1].format.fill.solid(); plot.series[1].format.fill.fore_color.rgb = BLUE
    bullets(s, [
        f"Returning visitors convert at {pct(vt['Returning']['conversion_rate'], 2)}, {vt['Returning']['conversion_rate'] / vt['New']['conversion_rate']:.1f}x the {pct(vt['New']['conversion_rate'], 2)} of first visits.",
        "Most buyers do not buy on their first visit, so first-visit conversion understates what acquisition traffic is worth.",
        "Action: capture first-time visitors (email sign-up, remarketing lists) and measure how many come back within 30 days.",
    ], Inches(8.4), Inches(1.8), Inches(4.4), Inches(5))
    footer(s, 8)

    db = r["depth"]
    picture_slide(prs, "Purchases come from long sessions; half of all visits end after one page",
                  "Conversion rate by pages viewed in the session", "depth_conversion.png", [
                      f"{pct(db['1 page']['session_share'])} of customer sessions view one page, and none of them buy.",
                      f"{pct(od['orders_with_10plus_pages_share'])} of purchases happen in sessions of 10+ pages.",
                      "Part of this is mechanical (cart and checkout are pages), so more pages is not a goal in itself.",
                      "Action: treat the one-page exits as a landing page problem. Rank landing pages by bounce rate and fix the worst ones first.",
                  ], 9)

    picture_slide(prs, "Engagement funnel: the biggest loss is the first click",
                  "Customer sessions reaching each depth", "funnel.png", [
                      f"{r['funnel']['Sessions']:,.0f} sessions, {r['funnel']['Engaged (2+ pages, no bounce)']:,.0f} engaged ({pct(r['funnel']['Engaged (2+ pages, no bounce)'] / r['funnel']['Sessions'])}).",
                      f"{r['funnel']['Deep (10+ pages)']:,.0f} reached 10+ pages and {r['funnel']['Purchased']:,.0f} bought.",
                      "Stages are defined by page depth because this export has no page-level or checkout-step events.",
                      "Next step: track add-to-cart and checkout steps as GA events to see the exact step where mobile buyers drop.",
                  ], 10)

    # 11. recommendations
    s = prs.slides.add_slide(prs.slide_layouts[6])
    add_title(s, "Recommendations, in order of effort")
    recs = [
        ("1. Filter internal traffic (days)", f"Exclude googleplex.com from the customer view. Every KPI after this is honest: conversion {pct(C['conversion_rate'], 2)}, not {pct(A['conversion_rate'], 2)}."),
        ("2. Fix mobile checkout (weeks)", f"A/B test a shorter mobile checkout. Mobile is {pct(dv['mobile']['session_share'])} of sessions; closing even a third of the conversion gap is a material revenue gain."),
        ("3. Re-measure social (days)", "Report YouTube and social on engagement and assisted conversions, and stop counting session spikes as growth."),
        ("4. Bring visitors back (ongoing)", f"Grow return visits: they convert {vt['Returning']['conversion_rate'] / vt['New']['conversion_rate']:.1f}x better and carry {pct(vt['Returning']['revenue_share'])} of revenue."),
        ("5. Scale paid search carefully (test)", f"Paid search converts at {pct(ch['Paid Search']['conversion_rate'], 2)} on {pct(ch['Paid Search']['session_share'])} of traffic. Raise budget in steps and watch cost per order."),
    ]
    tbl = s.shapes.add_table(len(recs), 2, Inches(0.5), Inches(1.8), Inches(12.3), Inches(4.8)).table
    tbl.columns[0].width, tbl.columns[1].width = Inches(3.6), Inches(8.7)
    for i, (a, b) in enumerate(recs):
        tbl.cell(i, 0).text, tbl.cell(i, 1).text = a, b
        for j in (0, 1):
            para = tbl.cell(i, j).text_frame.paragraphs[0]
            para.font.size, para.font.bold = Pt(14), (j == 0)
    footer(s, 11)

    # 12. appendix
    s = prs.slides.add_slide(prs.slide_layouts[6])
    add_title(s, "Appendix: data and definitions")
    d = r["data"]
    bullets(s, [
        f"Source: Google Merchandise Store GA export (Kaggle GA Customer Revenue Prediction, training file): {d['raw_rows']:,} sessions x {d['raw_columns']} fields, {d['first_date']} to {d['last_date']}. {d['kept_columns']} fields used.",
        f"{d['duplicate_session_id_rows']} session IDs appear on two dates: visits that crossed midnight, which GA splits into two sessions. Kept as GA counts them.",
        "Conversion = a session with revenue. The export has no order count, so one converting session is one order.",
        "Revenue = transactionRevenue / 1,000,000 (GA stores micro-units), US dollars. Monthly trend uses Aug 2016 to Jul 2017; 1 Aug 2017 is a partial day.",
        "Customers = all sessions not referred from googleplex.com. Other google.com referrers (Gmail, Sites, Groups) stay in, since outside users use them too.",
        "Confidence intervals: Wilson 95% on conversion rates; device gap tested with a two-proportion z-test. SQL in sql/kpis.sql, run with DuckDB.",
    ], Inches(0.5), Inches(1.8), Inches(12.3), Inches(5), size=14)
    footer(s, 12)

    cp = prs.core_properties
    cp.author = cp.last_modified_by = "Jayanshu Badlani"
    cp.title, cp.comments, cp.revision = OUT.stem.replace("_", " "), "", 1
    prs.save(OUT)
    return OUT


if __name__ == "__main__":
    print(build())
