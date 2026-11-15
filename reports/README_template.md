# Google Merchandise Store: Website Analytics

**Where does the store's traffic come from, which of it actually buys, and what should change?**

A year of Google Analytics sessions from the Google Merchandise Store (Google's own online shop
for branded clothing and accessories), analysed the way a digital analytics team would for a
monthly business review: define the KPIs, clean out the traffic that distorts them, break
performance down by channel, device and visitor type, and turn the findings into a short list
of actions. Deliverables are an Excel KPI workbook and a 12-slide insights deck.

## The answer in five lines

1. **Google's internal network inflates the numbers.** Sessions referred from googleplex.com, Google's
   corporate network (most likely staff), are {{i_sess_share}} of traffic but {{i_conv_share}} of purchases and {{i_rev_share}} of revenue.
   Taken out, the store's real customer conversion rate is **{{c_cr}}**, not the {{a_cr}} the unfiltered data shows.
2. **Mobile browses but does not buy.** Mobile is {{mob_sess}} of customer sessions and {{mob_rev}} of revenue.
   Mobile visitors view as many pages as desktop visitors and bounce no more often, yet convert **{{ratio}}x** less.
3. **The autumn 2016 traffic spike was YouTube, and it sold nothing.** Social reached {{soc_peak}} sessions
   in {{soc_peak_month}}; YouTube sent {{yt_sess}} sessions over the year and {{yt_conv}} purchases.
4. **Return visits carry the business.** Returning visitors are {{ret_sess}} of sessions and **{{ret_rev}}** of revenue.
5. **Direct and organic search earn the money.** Direct is {{dir_share}} of sessions and {{dir_rev}} of revenue.

## Deliverables

| File | What it is |
|---|---|
| `reports/GA_Store_KPI_Dashboard.xlsx` | Excel workbook: a dashboard sheet with KPI tiles and native charts, plus Channels, Devices, Visitor type, Countries, Monthly, Traffic source and Internal vs customers sheets. Every rate is a formula over raw counts, so any cell can be traced. |
| `reports/GA_Store_Insights.pptx` | 12-slide deck for a senior audience: summary, KPI snapshot, five findings with charts, recommendations, appendix on data and definitions. |
| `sql/kpis.sql` | All KPI queries, one named block per table, run with DuckDB. |
| `reports/tables/*.csv`, `reports/results.json` | Every number quoted here and in the deck. |

## The data

The training file of Kaggle's *Google Analytics Customer Revenue Prediction* dataset: the store's
real GA export, one row per session, **{{raw_rows}} sessions x {{raw_columns}} fields** (traffic source,
device, geography, and session totals such as pageviews, bounces and transaction revenue), from
1 Aug 2016 to 1 Aug 2017, covering {{visitors_all}} visitors. {{kept_columns}} of the fields are used.

Cleaning decisions, all in `src/load.py`:

| Issue | Rows | Decision |
|---|---|---|
| Revenue stored in micro-units | all | divided by 1,000,000 to get US dollars |
| Session ID on two dates | {{dups}} | visits that crossed midnight, which GA splits into two sessions; kept as GA counts them |
| Missing pageviews | {{missing_pv}} | set to 0 |
| Bounces and new-visit flags blank when false | most rows | blank read as 0 |
| Google's internal network (googleplex.com referrals) | {{i_sessions}} | flagged and reported separately from customers |
| 1 Aug 2017 is a single day | 1 day | left out of the monthly trend |

**KPI definitions.** Conversion rate = sessions with revenue / sessions. The export has no order
count, so one converting session is treated as one order. Bounce rate = single-interaction sessions
/ sessions. Revenue per session = revenue / sessions.

## Finding 1: internal traffic distorts every headline KPI

| KPI | All traffic | Customers | Internal (googleplex.com) |
|---|---|---|---|
| Sessions | {{a_sessions}} | {{c_sessions}} | {{i_sessions}} |
| Purchases | {{a_conv}} | {{c_conv}} | {{i_conv}} |
| Conversion rate | {{a_cr}} | {{c_cr}} | {{i_cr}} |
| Revenue | {{a_rev}} | {{c_rev}} | {{i_rev}} |
| Bounce rate | {{a_bounce}} | {{c_bounce}} | |
| Pages per session | {{a_pps}} | {{c_pps}} | |

Internal sessions convert at {{i_mult}}x the customer rate. Left in, they make the store look far
better at selling to the public than it is, and they hide how outside visitors behave. Only
googleplex.com is flagged: other google.com referrers (Gmail, Sites, Groups) are used by outside
people too, so they stay in the customer numbers. Everything below is customer traffic only.

![Internal share](reports/figures/internal_share.png)

## Finding 2: channels that bring traffic are not the ones that earn

| Channel | Sessions | Share | Bounce | Pages / session | Conversion | Share of revenue | Revenue / session |
|---|---|---|---|---|---|---|---|
{{channel_rows}}

![Traffic vs revenue](reports/figures/channel_traffic_vs_revenue.png)

- Direct visitors, people who type the address or use a bookmark, are the most valuable traffic.
- Paid search converts at {{ps_cr}} on only {{ps_share}} of sessions, the clearest channel to test more budget on.
- Display looks like the best channel per session, but {{disp_dfa}} of its revenue comes from one ad source
  (DoubleClick, `dfa`) and a single order is {{disp_top}} of it. That is too few orders to act on.
- The US is {{us_sess}} of customer sessions and {{us_rev}} of revenue.

![Conversion by channel](reports/figures/conversion_by_channel.png)

## Finding 3: the autumn 2016 spike was social, and revenue did not follow

Social sessions peaked at {{soc_peak}} in {{soc_peak_month}} and fell to an average of {{soc_late}} a
month by May to July 2017. YouTube was {{yt_share}} of all social sessions. Social traffic bounces
{{soc_bounce}} of the time; over the year it was {{soc_sess_share}} of customer sessions and {{soc_rev_share}} of revenue.
A dashboard that reports sessions would have shown autumn 2016 as a growth period. It was not.

![Monthly trend](reports/figures/monthly_trend.png)

## Finding 4: mobile visitors are interested, but do not buy

| Device | Sessions | Share | Bounce | Pages / session | Conversion | Share of revenue |
|---|---|---|---|---|---|---|
{{device_rows}}

Desktop converts {{ratio}}x better than mobile (two-proportion z = {{z}}). The obvious objection is
channel mix: maybe mobile traffic simply comes from weaker channels. It does not explain it. Inside
each channel with enough purchases on both devices ({{wc_channels}}), desktop still converts
{{wc_min}}x to {{wc_max}}x better. Because mobile visitors browse just as deeply, the drop is most
likely in the mobile cart and checkout, which is where testing should start.

![Device](reports/figures/device.png)

## Finding 5: most buyers come back before they buy

Returning visitors convert at {{ret_cr}} against {{new_cr}} for first visits ({{ret_mult}}x), and bring
{{ret_rev}} of revenue from {{ret_sess}} of sessions. A first-visit conversion rate therefore undervalues
acquisition channels: their visitors often buy on a later visit.

## Engagement depth and funnel

| Pages in session | Share of sessions | Conversion | Share of purchases |
|---|---|---|---|
{{depth_rows}}

{{one_page}} of sessions end after one page, and {{deep_share}} of purchases happen in sessions of 10 or
more pages. Part of that is mechanical, since the cart and checkout are pages themselves, so more
pageviews is not a goal by itself. The one-page exits are the actionable part: a landing page problem.

Funnel by depth: {{f_sess}} sessions, {{f_eng}} engaged (2+ pages), {{f_browse}} browsed 5+ pages,
{{f_deep}} reached 10+ pages, {{f_buy}} purchased. The export has no add-to-cart or checkout-step
events, so the funnel is defined by depth rather than by shopping steps.

![Funnel](reports/figures/funnel.png)

Customer order values: median {{median_order}}, 90th percentile {{p90_order}}, largest {{max_order}}.

## Recommendations

1. **Filter internal traffic.** Create a GA view or segment without googleplex.com referrals and report
   customers and staff separately. Real conversion is {{c_cr}}.
2. **Test a shorter mobile checkout.** Mobile is {{mob_sess}} of sessions; the conversion gap holds within channels.
3. **Measure social on engagement and assisted conversions,** not sessions, so a YouTube spike is not read as growth.
4. **Bring first-time visitors back** with email sign-up and remarketing; returning visits convert {{ret_mult}}x better.
5. **Scale paid search in steps,** watching cost per order, since it converts at {{ps_cr}} on a small share of traffic.

## How to run

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
kaggle datasets download colinpearse/ga-analytics-with-json-columns -f newtrain.csv -p data/raw --unzip
cd src && python run_all.py
pytest -q ../tests
```

`newtrain.csv` is the competition's `train.csv` with its JSON columns flattened (same {{raw_rows}}
sessions). `run_all.py` rebuilds the parquet file, every table and figure, the Excel workbook, the deck
and this README from `reports/README_template.md`.

## Limits

- One converting session is counted as one order; the export has no transaction count.
- Session-level data only: no page paths, product views or checkout steps, so funnel stages are depth based.
- Display and some country results rest on a handful of large orders and should not drive budget alone.
- Internal traffic is identified by referrer, so staff who arrive directly or through search are still counted as customers;
  the internal share above is a lower bound.
