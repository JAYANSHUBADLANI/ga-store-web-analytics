import sys
from pathlib import Path

import duckdb
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
import analysis  # noqa: E402
import load  # noqa: E402

HEADER = ("channelGrouping,date,fullVisitorId,sessionId,visitNumber,visitStartTime,device.deviceCategory,"
          "device.browser,device.operatingSystem,geoNetwork.continent,geoNetwork.country,trafficSource.source,"
          "trafficSource.medium,trafficSource.campaign,totals.hits,totals.pageviews,totals.bounces,totals.newVisits,"
          "totals.transactionRevenue")
ROWS = [
    "Organic Search,20170101,1,1_1,1,1483228800,desktop,Chrome,Windows,Americas,United States,google,organic,(not set),1,1,1,1,",
    "Referral,20170101,2,2_1,3,1483228900,desktop,Chrome,Macintosh,Americas,United States,mall.googleplex.com,referral,(not set),20,15,,,25990000",
    "Direct,20170102,3,3_1,2,1483315200,mobile,Safari,iOS,Americas,Canada,(direct),(none),(not set),12,10,,,10000000",
    "Social,20170102,4,4_1,1,1483315300,mobile,Chrome,Android,Asia,India,youtube.com,referral,(not set),2,,1,1,",
]


@pytest.fixture()
def built(tmp_path):
    raw = tmp_path / "raw.csv"
    raw.write_text(HEADER + "\n" + "\n".join(ROWS) + "\n")
    out = tmp_path / "sessions.parquet"
    stats = load.build(raw, out)
    con = duckdb.connect()
    return stats, con.execute(f"SELECT * FROM '{out}' ORDER BY session_id").df()


def test_revenue_is_converted_from_micros(built):
    _, df = built
    assert df.loc[df.session_id == "2_1", "revenue_usd"].item() == pytest.approx(25.99)
    assert df.loc[df.session_id == "3_1", "revenue_usd"].item() == pytest.approx(10.0)


def test_conversion_and_bounce_flags(built):
    _, df = built
    assert df["converted"].tolist() == [0, 1, 1, 0]
    assert df["bounced"].tolist() == [1, 0, 0, 1]


def test_missing_pageviews_become_zero(built):
    stats, df = built
    assert df.loc[df.session_id == "4_1", "pageviews"].item() == 0
    assert stats["sessions_missing_pageviews"] == 1


def test_only_googleplex_is_internal(built):
    _, df = built
    assert df["is_internal"].tolist() == [0, 1, 0, 0]


def test_sql_file_parses_into_named_queries():
    q = analysis.load_queries()
    assert {"headline", "by_channel", "by_device", "funnel", "monthly"} <= set(q)
    assert all(not v.rstrip().endswith(";") for v in q.values())


def test_wilson_interval_contains_rate_and_stays_in_bounds():
    lo, hi = analysis.wilson([0, 5, 100], [100, 100, 100])
    assert lo[0] == pytest.approx(0, abs=1e-12) and hi[2] == pytest.approx(1, abs=1e-12)
    assert lo[1] < 0.05 < hi[1]


def test_two_proportion_z_sign_and_symmetry():
    z1, p1 = analysis.two_prop_z(90, 1000, 40, 1000)
    z2, p2 = analysis.two_prop_z(40, 1000, 90, 1000)
    assert z1 > 0 and z1 == pytest.approx(-z2) and p1 == pytest.approx(p2) and p1 < 0.001
