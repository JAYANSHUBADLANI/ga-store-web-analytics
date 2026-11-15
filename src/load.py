"""Load the raw Google Analytics session export and write a typed session table.

The raw file has one row per session and 55 flattened GA fields, all read as text.
This step keeps the fields used in the analysis, converts them to proper types and
adds the flags every later query relies on (converted, bounced, new visitor, internal
traffic). Output: data/processed/sessions.parquet
"""
from pathlib import Path

import duckdb

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw" / "newtrain.csv"
OUT = ROOT / "data" / "processed" / "sessions.parquet"

# googleplex.com is Google's internal corporate network. Sessions referred from it are
# employees shopping on their own company store, not outside customers. Only that domain
# is flagged; other google.com referrers (Gmail, Sites, Groups) can be outside users too,
# so they stay in the customer traffic.
INTERNAL_DOMAIN = "googleplex.com"

BUILD_SQL = """
CREATE OR REPLACE TABLE sessions AS
SELECT
    sessionId                                              AS session_id,
    fullVisitorId                                          AS visitor_id,
    strptime(date, '%Y%m%d')::DATE                         AS session_date,
    to_timestamp(CAST(visitStartTime AS BIGINT))           AS start_time_utc,
    CAST(visitNumber AS INTEGER)                           AS visit_number,
    channelGrouping                                        AS channel,
    "device.deviceCategory"                                AS device,
    "device.browser"                                       AS browser,
    "device.operatingSystem"                               AS os,
    "geoNetwork.continent"                                 AS continent,
    "geoNetwork.country"                                   AS country,
    "trafficSource.source"                                 AS source,
    "trafficSource.medium"                                 AS medium,
    "trafficSource.campaign"                               AS campaign,
    COALESCE(TRY_CAST("totals.hits" AS INTEGER), 0)        AS hits,
    COALESCE(TRY_CAST("totals.pageviews" AS INTEGER), 0)   AS pageviews,
    COALESCE(TRY_CAST("totals.bounces" AS INTEGER), 0)     AS bounced,
    COALESCE(TRY_CAST("totals.newVisits" AS INTEGER), 0)   AS is_new_visitor,
    COALESCE(TRY_CAST("totals.transactionRevenue" AS DOUBLE), 0) / 1e6 AS revenue_usd,
    CASE WHEN COALESCE(TRY_CAST("totals.transactionRevenue" AS DOUBLE), 0) > 0 THEN 1 ELSE 0 END AS converted,
    CASE WHEN "trafficSource.source" LIKE '%' || ? THEN 1 ELSE 0 END AS is_internal
FROM read_csv(?, all_varchar = true, header = true)
"""


def build(raw: Path = RAW, out: Path = OUT) -> dict:
    con = duckdb.connect()
    con.execute(BUILD_SQL, [INTERNAL_DOMAIN, str(raw)])
    out.parent.mkdir(parents=True, exist_ok=True)
    con.execute(f"COPY sessions TO '{out}' (FORMAT PARQUET)")
    raw_cols = len(con.execute("SELECT * FROM read_csv(?, all_varchar = true, header = true) LIMIT 0", [str(raw)]).description)
    stats = con.execute("""
        SELECT COUNT(*), COUNT(DISTINCT session_id), COUNT(DISTINCT visitor_id),
               MIN(session_date), MAX(session_date),
               SUM(CASE WHEN pageviews = 0 THEN 1 ELSE 0 END)
        FROM sessions""").fetchone()
    return {
        "raw_rows": stats[0], "raw_columns": raw_cols, "kept_columns": len(con.execute("SELECT * FROM sessions LIMIT 0").description),
        "unique_session_ids": stats[1], "duplicate_session_id_rows": stats[0] - stats[1],
        "visitors": stats[2], "first_date": str(stats[3]), "last_date": str(stats[4]),
        "sessions_missing_pageviews": stats[5],
    }


if __name__ == "__main__":
    print(build())
