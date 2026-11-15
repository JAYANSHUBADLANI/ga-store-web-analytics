-- KPI queries for the Google Merchandise Store session data.
-- Each block starts with "-- name: <table>" and is run by src/analysis.py against
-- data/processed/sessions.parquet. "customers" excludes Google's internal
-- (googleplex.com) traffic; "sessions" is everything GA recorded.
--
-- KPI definitions used throughout
--   conversion rate   = sessions with revenue / sessions
--   bounce rate       = single-interaction sessions / sessions
--   pages per session = pageviews / sessions
--   revenue per session (RPS) = revenue / sessions
--   revenue per order = revenue / converting sessions (the export has no order count,
--                       so each converting session is treated as one order)

-- name: headline
SELECT 'All traffic' AS segment,
       COUNT(*) AS sessions, COUNT(DISTINCT visitor_id) AS visitors,
       AVG(is_new_visitor) AS new_session_share, AVG(bounced) AS bounce_rate,
       SUM(pageviews) * 1.0 / COUNT(*) AS pages_per_session,
       SUM(converted) AS conversions, AVG(converted) AS conversion_rate,
       SUM(revenue_usd) AS revenue, SUM(revenue_usd) / COUNT(*) AS revenue_per_session,
       SUM(revenue_usd) / NULLIF(SUM(converted), 0) AS revenue_per_order
FROM sessions
UNION ALL
SELECT CASE WHEN is_internal = 1 THEN 'Internal (googleplex.com)' ELSE 'Customers (external)' END,
       COUNT(*), COUNT(DISTINCT visitor_id), AVG(is_new_visitor), AVG(bounced),
       SUM(pageviews) * 1.0 / COUNT(*), SUM(converted), AVG(converted),
       SUM(revenue_usd), SUM(revenue_usd) / COUNT(*), SUM(revenue_usd) / NULLIF(SUM(converted), 0)
FROM sessions GROUP BY is_internal;

-- name: by_channel
SELECT channel,
       COUNT(*) AS sessions,
       COUNT(*) * 1.0 / SUM(COUNT(*)) OVER () AS session_share,
       AVG(bounced) AS bounce_rate,
       SUM(pageviews) * 1.0 / COUNT(*) AS pages_per_session,
       SUM(converted) AS conversions,
       AVG(converted) AS conversion_rate,
       SUM(revenue_usd) AS revenue,
       SUM(revenue_usd) / SUM(SUM(revenue_usd)) OVER () AS revenue_share,
       SUM(revenue_usd) / COUNT(*) AS revenue_per_session
FROM customers GROUP BY channel ORDER BY sessions DESC;

-- name: by_device
SELECT device,
       COUNT(*) AS sessions,
       COUNT(*) * 1.0 / SUM(COUNT(*)) OVER () AS session_share,
       AVG(bounced) AS bounce_rate,
       SUM(pageviews) * 1.0 / COUNT(*) AS pages_per_session,
       SUM(converted) AS conversions,
       AVG(converted) AS conversion_rate,
       SUM(revenue_usd) AS revenue,
       SUM(revenue_usd) / SUM(SUM(revenue_usd)) OVER () AS revenue_share,
       SUM(revenue_usd) / NULLIF(SUM(converted), 0) AS revenue_per_order
FROM customers GROUP BY device ORDER BY sessions DESC;

-- name: channel_device
SELECT channel, device, COUNT(*) AS sessions, SUM(converted) AS conversions,
       AVG(converted) AS conversion_rate
FROM customers
WHERE device IN ('desktop', 'mobile')
GROUP BY channel, device ORDER BY channel, device;

-- name: visitor_type
SELECT CASE WHEN visit_number = 1 THEN 'New' ELSE 'Returning' END AS visitor_type,
       COUNT(*) AS sessions,
       COUNT(*) * 1.0 / SUM(COUNT(*)) OVER () AS session_share,
       AVG(bounced) AS bounce_rate,
       SUM(pageviews) * 1.0 / COUNT(*) AS pages_per_session,
       SUM(converted) AS conversions,
       AVG(converted) AS conversion_rate,
       SUM(revenue_usd) AS revenue,
       SUM(revenue_usd) / SUM(SUM(revenue_usd)) OVER () AS revenue_share
FROM customers GROUP BY 1 ORDER BY 1;

-- name: depth_bands
SELECT CASE WHEN pageviews <= 1 THEN '1 page'
            WHEN pageviews <= 3 THEN '2-3 pages'
            WHEN pageviews <= 9 THEN '4-9 pages'
            WHEN pageviews <= 19 THEN '10-19 pages'
            ELSE '20+ pages' END AS depth,
       MIN(pageviews) AS sort_key,
       COUNT(*) AS sessions,
       COUNT(*) * 1.0 / SUM(COUNT(*)) OVER () AS session_share,
       SUM(converted) AS conversions,
       AVG(converted) AS conversion_rate,
       SUM(converted) * 1.0 / SUM(SUM(converted)) OVER () AS conversion_share
FROM customers GROUP BY 1 ORDER BY sort_key;

-- name: funnel
SELECT 'Sessions' AS stage, 1 AS step, COUNT(*) AS sessions FROM customers
UNION ALL SELECT 'Engaged (2+ pages, no bounce)', 2, COUNT(*) FROM customers WHERE bounced = 0 AND pageviews >= 2
UNION ALL SELECT 'Browsed (5+ pages)', 3, COUNT(*) FROM customers WHERE pageviews >= 5
UNION ALL SELECT 'Deep (10+ pages)', 4, COUNT(*) FROM customers WHERE pageviews >= 10
UNION ALL SELECT 'Purchased', 5, COUNT(*) FROM customers WHERE converted = 1
ORDER BY step;

-- name: monthly
SELECT strftime(session_date, '%Y-%m') AS month,
       COUNT(*) AS sessions,
       SUM(CASE WHEN is_internal = 0 THEN 1 ELSE 0 END) AS customer_sessions,
       SUM(CASE WHEN channel = 'Social' AND is_internal = 0 THEN 1 ELSE 0 END) AS social_sessions,
       SUM(CASE WHEN is_internal = 0 THEN converted ELSE 0 END) AS customer_conversions,
       SUM(CASE WHEN is_internal = 0 THEN revenue_usd ELSE 0 END) AS customer_revenue,
       SUM(CASE WHEN is_internal = 1 THEN revenue_usd ELSE 0 END) AS internal_revenue
FROM sessions
WHERE session_date < DATE '2017-08-01'      -- the export ends with one partial day
GROUP BY 1 ORDER BY 1;

-- name: top_countries
SELECT country, COUNT(*) AS sessions, SUM(converted) AS conversions,
       AVG(converted) AS conversion_rate, SUM(revenue_usd) AS revenue,
       SUM(revenue_usd) / SUM(SUM(revenue_usd)) OVER () AS revenue_share
FROM customers GROUP BY country ORDER BY sessions DESC LIMIT 10;

-- name: social_sources
SELECT source, COUNT(*) AS sessions, AVG(bounced) AS bounce_rate,
       SUM(pageviews) * 1.0 / COUNT(*) AS pages_per_session,
       SUM(converted) AS conversions, SUM(revenue_usd) AS revenue
FROM customers WHERE channel = 'Social'
GROUP BY source ORDER BY sessions DESC LIMIT 8;

-- name: weekday
SELECT dayname(session_date) AS weekday, isodow(session_date) AS dow,
       COUNT(*) AS sessions, AVG(converted) AS conversion_rate, SUM(revenue_usd) AS revenue
FROM customers GROUP BY 1, 2 ORDER BY dow;
