"""Task 3 business queries.

Run from the repository root, with Neo4j up and `.env` filled in:

    PYTHONPATH=src python -m tradekg.queries

Each query keeps one shipment node per bill of lading: the row with the
lowest shipment_id. The other row of a duplicate bill is a second filing of
the same document. Buyers and suppliers are companies (`party_kind = company`).
Banks, forwarders, and the To Order party stay on the shipment and are not
treated as customers or suppliers.
"""

from __future__ import annotations

import json
import time
from pathlib import Path

from tradekg.graph import database_name, load_env, open_database

ROOT = Path(__file__).resolve().parents[2]
REPORT_PATH = ROOT / "reports" / "task3_results.json"

# Alternative suppliers of one HS code for one buyer, excluding one origin.
# Origin is the shipment's ORIGINATED_IN country, not the supplier's registration.
QUERY_A = """
MATCH (buyer:Company {entity_id: $buyer_id})
MATCH (hs:HSCode {hs_code: $hs_code})
MATCH (excluded:Country {iso2: $exclude_origin})
OPTIONAL MATCH (buyer)<-[:CONSIGNED_TO]-(current_shipment:Shipment)-[:CLASSIFIED_AS]->(hs)
OPTIONAL MATCH (current:Company)-[:SHIPPED]->(current_shipment)
WHERE current.party_kind = 'company'
WITH buyer, hs, excluded,
     [c IN collect(DISTINCT current) WHERE c IS NOT NULL] AS current_suppliers
MATCH (supplier:Company)-[:SHIPPED]->(s:Shipment)-[:CLASSIFIED_AS]->(hs)
MATCH (s)-[:ORIGINATED_IN]->(origin:Country)
WHERE supplier.party_kind = 'company'
  AND supplier.on_platform = true
  AND supplier <> buyer
  AND NOT supplier IN current_suppliers
  AND origin <> excluded
WITH supplier, s.bill_of_lading AS bill, s, origin
ORDER BY s.shipment_id
WITH supplier, bill, head(collect(s)) AS s, head(collect(origin)) AS origin
WITH supplier,
     count(*) AS bills,
     sum(s.value_usd) AS export_value,
     collect(DISTINCT origin.iso2) AS origins
RETURN supplier.entity_id AS entity_id,
       supplier.canonical_name AS supplier,
       supplier.activity_class AS activity,
       bills,
       round(export_value) AS export_value_usd,
       origins
ORDER BY bills DESC, export_value_usd DESC
"""

# Buyers of a category with no interaction, in either direction, with a platform seller.
QUERY_B = """
MATCH (category:Category {name: $category})<-[:IN_CATEGORY]-(:HSCode)
      <-[:CLASSIFIED_AS]-(s:Shipment)-[:CONSIGNED_TO]->(buyer:Company)
WHERE buyer.party_kind = 'company'
WITH buyer, s.bill_of_lading AS bill, s
ORDER BY s.shipment_id
WITH buyer, bill, head(collect(s)) AS s
WITH buyer, count(*) AS bills, sum(s.value_usd) AS import_value
WHERE NOT EXISTS {
  MATCH (buyer)-[:PERFORMED]->(:Interaction)-[:DIRECTED_AT]->(seller:Company)
  WHERE seller.on_platform = true
    AND seller.party_kind = 'company'
    AND (EXISTS { MATCH (seller)-[:OFFERS]->(:Product) }
         OR EXISTS { MATCH (seller)-[:SHIPPED]->(:Shipment) })
}
AND NOT EXISTS {
  MATCH (seller:Company)-[:PERFORMED]->(:Interaction)-[:DIRECTED_AT]->(buyer)
  WHERE seller.on_platform = true
    AND seller.party_kind = 'company'
    AND (EXISTS { MATCH (seller)-[:OFFERS]->(:Product) }
         OR EXISTS { MATCH (seller)-[:SHIPPED]->(:Shipment) })
}
RETURN buyer.entity_id AS entity_id,
       buyer.canonical_name AS buyer_name,
       buyer.on_platform AS on_platform,
       bills,
       round(import_value) AS import_value_usd
ORDER BY on_platform DESC, import_value_usd DESC
"""

# Sellers whose largest company buyer is more than 60% of export value.
QUERY_C = """
MATCH (seller:Company)-[:SHIPPED]->(s:Shipment)-[:CONSIGNED_TO]->(buyer:Company)
WHERE seller.party_kind = 'company'
  AND buyer.party_kind = 'company'
  AND seller <> buyer
  AND s.value_usd IS NOT NULL
WITH seller, s.bill_of_lading AS bill, s, buyer
ORDER BY s.shipment_id
WITH seller, bill, head(collect(s)) AS s, head(collect(buyer)) AS buyer
WITH seller, buyer,
     sum(s.value_usd) AS buyer_value,
     count(*) AS buyer_bills
WITH seller, collect({
       id: buyer.entity_id,
       name: buyer.canonical_name,
       on_platform: buyer.on_platform,
       value: buyer_value,
       bills: buyer_bills
     }) AS rows
WITH seller, rows,
     reduce(top = null, r IN rows |
       CASE
         WHEN top IS NULL
           OR r.value > top.value
           OR (r.value = top.value AND r.id < top.id)
         THEN r ELSE top
       END) AS top,
     reduce(total = 0.0, r IN rows | total + r.value) AS export_value,
     reduce(bills = 0, r IN rows | bills + r.bills) AS bills
WHERE export_value > 0 AND top.value > 0.6 * export_value
RETURN seller.entity_id AS entity_id,
       seller.canonical_name AS seller,
       seller.on_platform AS on_platform,
       seller.activity_class AS activity,
       top.name AS top_buyer,
       top.id AS top_buyer_id,
       top.on_platform AS buyer_on_platform,
       round(1000.0 * top.value / export_value) / 10.0 AS share_pct,
       round(export_value) AS export_value_usd,
       top.bills AS top_buyer_bills,
       bills,
       size(rows) AS buyers
ORDER BY export_value_usd DESC
"""

# Five companies with the closest shipment pattern to a seed company.
# A pattern is the bill-weighted set of (HS code, origin, destination) lanes.
QUERY_D = """
MATCH (seed:Company {entity_id: $company_id})
MATCH (seed)-[:SHIPPED]->(s:Shipment)
WITH s.bill_of_lading AS bill, s
ORDER BY s.shipment_id
WITH bill, head(collect(s)) AS s
MATCH (s)-[:CLASSIFIED_AS]->(h:HSCode)
MATCH (s)-[:ORIGINATED_IN]->(o:Country)
MATCH (s)-[:DESTINED_FOR]->(d:Country)
WITH h.hs_code + '|' + o.iso2 + '|' + d.iso2 AS lane, count(*) AS weight
WITH collect({k: lane, w: weight}) AS seed_features,
     sqrt(sum(toFloat(weight) * weight)) AS seed_norm
WHERE seed_norm > 0
MATCH (other:Company)-[:SHIPPED]->(s:Shipment)
WHERE other.party_kind = 'company' AND other.entity_id <> $company_id
WITH seed_features, seed_norm, other, s.bill_of_lading AS bill, s
ORDER BY s.shipment_id
WITH seed_features, seed_norm, other, bill, head(collect(s)) AS s
MATCH (s)-[:CLASSIFIED_AS]->(h:HSCode)
MATCH (s)-[:ORIGINATED_IN]->(o:Country)
MATCH (s)-[:DESTINED_FOR]->(d:Country)
WITH seed_features, seed_norm, other,
     h.hs_code + '|' + o.iso2 + '|' + d.iso2 AS lane,
     count(*) AS weight
WITH seed_features, seed_norm, other,
     collect({k: lane, w: weight}) AS other_features,
     sum(weight) AS bills,
     sqrt(sum(toFloat(weight) * weight)) AS other_norm
WHERE bills >= $min_bills AND other_norm > 0
UNWIND other_features AS yf
WITH other, bills, other_norm, seed_norm, yf,
     head([xf IN seed_features WHERE xf.k = yf.k]) AS xf
WITH other, bills, other_norm, seed_norm,
     sum(CASE WHEN xf IS NULL THEN 0.0 ELSE toFloat(xf.w) * toFloat(yf.w) END) AS dot,
     [lane IN collect(CASE WHEN xf IS NULL THEN NULL ELSE yf.k END)
      WHERE lane IS NOT NULL] AS shared_lanes
WHERE dot > 0
RETURN other.entity_id AS entity_id,
       other.canonical_name AS company,
       other.on_platform AS on_platform,
       other.activity_class AS activity,
       bills AS classified_bills,
       round(1000.0 * dot / (seed_norm * other_norm)) / 1000.0 AS cosine,
       shared_lanes
ORDER BY cosine DESC, classified_bills DESC
LIMIT 5
"""

PARAMS_A = {
    "buyer_id": "ENT-01800",
    "hs_code": "870899",
    "exclude_origin": "CN",
}
PARAMS_B = {"category": "Agriculture & Food"}
PARAMS_D = {"company_id": "ENT-00293", "min_bills": 10}


def _ms(value) -> int:
    if value is None:
        return 0
    return int(value)


def run_query(session, query: str, params: dict) -> tuple[list[dict], int]:
    """Run once to warm the page cache, then time a second execution."""
    session.run(query, params).consume()
    started = time.perf_counter()
    result = session.run(query, params)
    rows = [dict(record) for record in result]
    summary = result.consume()
    wall_ms = int((time.perf_counter() - started) * 1000)
    server_ms = _ms(summary.result_available_after) + _ms(summary.result_consumed_after)
    for row in rows:
        row["_server_ms"] = server_ms
        row["_wall_ms"] = wall_ms
    return rows, server_ms


def _plain(rows: list[dict]) -> list[dict]:
    cleaned = []
    for row in rows:
        item = {}
        for key, value in row.items():
            if key.startswith("_"):
                continue
            if isinstance(value, float) and value.is_integer() and key.endswith("_usd"):
                value = int(value)
            elif isinstance(value, list) and all(isinstance(entry, str) for entry in value):
                value = sorted(value)
            elif hasattr(value, "isoformat"):
                value = value.isoformat()
            item[key] = value
        cleaned.append(item)
    return cleaned


def main() -> None:
    load_env(ROOT)
    driver = open_database()
    try:
        with driver.session(database=database_name()) as session:
            names = session.run(
                """
                MATCH (buyer:Company {entity_id: $buyer_id})
                MATCH (seed:Company {entity_id: $company_id})
                MATCH (hs:HSCode {hs_code: $hs_code})
                MATCH (origin:Country {iso2: $exclude_origin})
                RETURN buyer.canonical_name AS buyer,
                       seed.canonical_name AS seed,
                       hs.description AS hs_description,
                       origin.name AS origin_name
                """,
                {**PARAMS_A, "company_id": PARAMS_D["company_id"]},
            ).single()
            rows_a, ms_a = run_query(session, QUERY_A, PARAMS_A)
            rows_b, ms_b = run_query(session, QUERY_B, PARAMS_B)
            rows_c, ms_c = run_query(session, QUERY_C, {})
            rows_d, ms_d = run_query(session, QUERY_D, PARAMS_D)
    finally:
        driver.close()

    on_platform_b = sum(1 for row in rows_b if row["on_platform"])
    on_platform_c = sum(1 for row in rows_c if row["on_platform"])
    report = {
        "parameters": {
            "a": {**PARAMS_A, "buyer_name": names["buyer"], "hs_description": names["hs_description"], "origin_name": names["origin_name"]},
            "b": PARAMS_B,
            "d": {**PARAMS_D, "company_name": names["seed"]},
        },
        "runtime_ms": {"a": ms_a, "b": ms_b, "c": ms_c, "d": ms_d},
        "counts": {
            "a": len(rows_a),
            "b": len(rows_b),
            "b_on_platform": on_platform_b,
            "b_off_platform": len(rows_b) - on_platform_b,
            "c": len(rows_c),
            "c_on_platform": on_platform_c,
            "c_off_platform": len(rows_c) - on_platform_c,
        },
        "sample": {
            "a": _plain(rows_a[:10]),
            "b": _plain(rows_b[:10]),
            "c": _plain(rows_c[:10]),
            "d": _plain(rows_d),
        },
    }
    REPORT_PATH.parent.mkdir(exist_ok=True)
    REPORT_PATH.write_text(json.dumps(report, indent=2) + "\n")
    print(f"Wrote {REPORT_PATH.relative_to(ROOT)}")
    print(
        "runtimes ms "
        f"a={ms_a} b={ms_b} c={ms_c} d={ms_d} "
        f"counts a={len(rows_a)} b={len(rows_b)} c={len(rows_c)} d={len(rows_d)}"
    )


if __name__ == "__main__":
    main()
