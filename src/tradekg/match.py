"""Rank platform sellers for a parsed RFQ and write the parse onto the graph.

Retrieval follows the ontology. Start at the HS code when the parse kept one.
Keep a seller only when the shipment was not produced in an excluded origin,
the goods were delivered to the requested country or port, and the seller holds
every requested certificate. If that set is empty, drop one constraint at a
time: certificates, then delivery, then the HS code (back to the category),
then the excluded origin. The first non-empty set is the ranking.

The explanation cites counts on that path. A bill of lading is counted once.

    PYTHONPATH=src python -m tradekg.match
"""

from __future__ import annotations

import json
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date, timedelta
from pathlib import Path

from tradekg.graph import database_name, load_env, open_database
from tradekg.reference import all_certifications
from tradekg.rfq_parse import ParsedRFQ, load_hs_categories, parse_rfq

ROOT = Path(__file__).resolve().parents[2]
REPORT_PATH = ROOT / "reports" / "task4_matches.json"
POC_IDS = ["RFQ-0007", "RFQ-0027", "RFQ-0052", "RFQ-0257", "RFQ-0399"]

_CERT_NAME = {row["code"]: row["name"] for row in all_certifications()}


@dataclass
class Bill:
    shipment_id: str
    bill: str
    hs: str
    category: str
    origin: str | None
    dest: str | None
    port: str | None
    shipped: date | None
    value: float | None


@dataclass
class Seller:
    entity_id: str
    name: str
    activity: str | None
    bills: list[Bill] = field(default_factory=list)
    listings: list[tuple[str, str]] = field(default_factory=list)
    certs: set[str] = field(default_factory=set)


def _as_date(value) -> date | None:
    if value is None:
        return None
    if isinstance(value, date):
        return value
    text = value.iso_format() if hasattr(value, "iso_format") else str(value)
    return date.fromisoformat(text[:10])


def _load_graph(session) -> tuple[dict[str, Seller], dict[str, dict], dict[str, list[str]]]:
    sellers: dict[str, Seller] = {}

    def seller_of(record) -> Seller:
        entity_id = record["entity_id"]
        found = sellers.get(entity_id)
        if found is None:
            found = Seller(
                entity_id=entity_id,
                name=record["name"],
                activity=record["activity"],
            )
            sellers[entity_id] = found
        return found

    shipment_rows = session.run(
        """
        MATCH (seller:Company)-[:SHIPPED]->(s:Shipment)-[:CLASSIFIED_AS]->(h:HSCode)
              -[:IN_CATEGORY]->(cat:Category)
        WHERE seller.on_platform = true AND seller.party_kind = 'company'
        OPTIONAL MATCH (s)-[:ORIGINATED_IN]->(o:Country)
        OPTIONAL MATCH (s)-[:DESTINED_FOR]->(d:Country)
        OPTIONAL MATCH (s)-[:DISCHARGED_AT]->(p:Port)
        RETURN seller.entity_id AS entity_id,
               seller.canonical_name AS name,
               seller.activity_class AS activity,
               s.shipment_id AS shipment_id,
               s.bill_of_lading AS bill,
               s.shipment_date AS shipment_date,
               s.value_usd AS value_usd,
               h.hs_code AS hs_code,
               cat.name AS category,
               o.iso2 AS origin,
               d.iso2 AS dest,
               p.port_id AS port_id
        """
    )
    grouped: dict[tuple[str, str], dict] = {}
    for record in shipment_rows:
        key = (record["entity_id"], record["bill"] or record["shipment_id"])
        current = grouped.get(key)
        if current is None or record["shipment_id"] < current["shipment_id"]:
            grouped[key] = dict(record)
    for record in grouped.values():
        seller = seller_of(record)
        seller.bills.append(Bill(
            shipment_id=record["shipment_id"],
            bill=record["bill"] or record["shipment_id"],
            hs=record["hs_code"],
            category=record["category"],
            origin=record["origin"],
            dest=record["dest"],
            port=record["port_id"],
            shipped=_as_date(record["shipment_date"]),
            value=record["value_usd"],
        ))

    for record in session.run(
        """
        MATCH (seller:Company)-[:OFFERS]->(p:Product)-[:CLASSIFIED_AS]->(h:HSCode)
        WHERE seller.on_platform = true AND seller.party_kind = 'company'
        RETURN seller.entity_id AS entity_id,
               seller.canonical_name AS name,
               seller.activity_class AS activity,
               p.title AS title,
               h.hs_code AS hs_code
        """
    ):
        seller_of(record).listings.append((record["title"], record["hs_code"]))

    for record in session.run(
        """
        MATCH (seller:Company)-[:HOLDS]->(c:Certification)
        WHERE seller.on_platform = true AND seller.party_kind = 'company'
        RETURN seller.entity_id AS entity_id,
               seller.canonical_name AS name,
               seller.activity_class AS activity,
               collect(c.code) AS codes
        """
    ):
        seller_of(record).certs.update(record["codes"])

    rfqs = {}
    for record in session.run(
        """
        MATCH (buyer:Company)-[:POSTED]->(r:RFQ)
        RETURN r.rfq_id AS rfq_id, r.text AS text, r.created_at AS created_at,
               r.status AS status, buyer.entity_id AS buyer_id,
               buyer.canonical_name AS buyer_name
        """
    ):
        rfqs[record["rfq_id"]] = {
            "text": record["text"],
            "created_at": str(record["created_at"]),
            "status": record["status"],
            "buyer_id": record["buyer_id"],
            "buyer_name": record["buyer_name"],
        }

    responders: dict[str, list[str]] = defaultdict(list)
    for record in session.run(
        """
        MATCH (seller:Company)-[:PERFORMED]->(e:Interaction {event_type: 'rfq_response'})
              -[:ABOUT_RFQ]->(r:RFQ)
        RETURN r.rfq_id AS rfq_id, collect(DISTINCT seller.entity_id) AS sellers
        """
    ):
        responders[record["rfq_id"]] = list(record["sellers"])
    return sellers, rfqs, responders


def _bills_for(seller: Seller, hs_codes: set[str] | None, categories: set[str], excluded: set[str]) -> list[Bill]:
    kept = []
    for bill in seller.bills:
        if hs_codes is not None and bill.hs not in hs_codes:
            continue
        if hs_codes is None and bill.category not in categories:
            continue
        if bill.origin in excluded:
            continue
        kept.append(bill)
    return kept


def _listings_for(seller: Seller, hs_codes: set[str] | None, categories: set[str], hs_category: dict[str, str]) -> list[tuple[str, str]]:
    kept = []
    for title, code in seller.listings:
        if hs_codes is not None and code in hs_codes:
            kept.append((title, code))
        elif hs_codes is None and hs_category.get(code) in categories:
            kept.append((title, code))
    return kept


def _explain(seller: Seller, rows: list[Bill], listed: list[tuple[str, str]], parsed: ParsedRFQ, as_of: date) -> str:
    start = as_of - timedelta(days=365)
    delivered = [
        bill for bill in rows
        if (parsed.dest_iso and bill.dest == parsed.dest_iso)
        or (parsed.port_id and bill.port == parsed.port_id)
    ]
    window = [bill for bill in delivered if bill.shipped and start <= bill.shipped <= as_of]
    sentences = []
    focus = window or delivered or rows
    if focus:
        counts: dict[str, int] = defaultdict(int)
        for bill in focus:
            counts[bill.hs] += 1
        hs_code, count = max(counts.items(), key=lambda item: (item[1], item[0]))
        if window and parsed.dest_name:
            times = "once" if count == 1 else f"{count} times"
            sentences.append(
                f"Exported HS {hs_code} to {parsed.dest_name} {times} "
                "in the 12 months before this request."
            )
        elif delivered and parsed.dest_name:
            times = "once" if count == 1 else f"{count} times"
            sentences.append(f"Exported HS {hs_code} to {parsed.dest_name} {times}.")
        else:
            times = "once" if count == 1 else f"{count} times"
            sentences.append(f"Exported HS {hs_code} {times}.")
        others = [code for code in counts if code != hs_code]
        if others:
            sentences.append("Also exported HS " + ", ".join(sorted(others)) + ".")
    elif listed:
        title, code = listed[0]
        sentences.append(f"Lists {title}, classified as HS {code}.")

    preferred = {iso: name for iso, name, _raw in parsed.prefers}
    origin_names = sorted({preferred[bill.origin] for bill in rows if bill.origin in preferred})
    if origin_names:
        sentences.append("Shipments of this code originated in " + " and ".join(origin_names) + ".")

    if parsed.port_id:
        discharged = sum(1 for bill in focus if bill.port == parsed.port_id)
        if discharged and parsed.port_name:
            sentences.append(f"Discharged at {parsed.port_name} on {discharged} of those bills.")

    held = [_CERT_NAME.get(code, code) for code, _raw in parsed.certs if code in seller.certs]
    if held:
        if len(held) == 1:
            sentences.append(f"Holds {held[0]}.")
        else:
            sentences.append("Holds " + ", ".join(held[:-1]) + " and " + held[-1] + ".")
    return " ".join(sentences)


def rank_sellers(parsed: ParsedRFQ, sellers: dict[str, Seller], buyer_id: str, as_of: date, hs_category: dict[str, str]) -> dict:
    sought_hs = {product.hs_code for product in parsed.products if product.hs_code}
    sought_categories = {product.category for product in parsed.products if product.category}
    required = [code for code, _raw in parsed.certs]
    excluded = {iso for iso, _name, _raw in parsed.excludes}
    has_lane = bool(parsed.dest_iso or parsed.port_id)

    def collect(use_hs: bool, use_lane: bool, use_certs: bool, use_origin: bool):
        found = []
        hs_filter = sought_hs if use_hs else None
        blocked = excluded if use_origin else set()
        for seller in sellers.values():
            if seller.entity_id == buyer_id:
                continue
            rows = _bills_for(seller, hs_filter, sought_categories, blocked)
            listed = _listings_for(seller, hs_filter, sought_categories, hs_category)
            if not rows and not listed:
                continue
            if use_lane and has_lane:
                lane = [
                    bill for bill in rows
                    if (parsed.dest_iso and bill.dest == parsed.dest_iso)
                    or (parsed.port_id and bill.port == parsed.port_id)
                ]
                if not lane:
                    continue
            else:
                lane = rows
            if use_certs and required and not all(code in seller.certs for code in required):
                continue
            found.append((seller, rows, lane, listed))
        return found

    full = {
        "hs": bool(sought_hs),
        "lane": has_lane,
        "certs": bool(required),
        "origin": bool(excluded),
    }
    masks = [dict(full)]
    current = dict(full)
    for key in ("certs", "lane", "hs", "origin"):
        if current[key]:
            current[key] = False
            masks.append(dict(current))

    chosen = []
    used = dict(full)
    for mask in masks:
        chosen = collect(mask["hs"], mask["lane"], mask["certs"], mask["origin"])
        if chosen:
            used = mask
            break

    relaxed = []
    if full["certs"] and not used["certs"]:
        relaxed.append("certificate")
    if full["lane"] and not used["lane"]:
        relaxed.append("delivery")
    if full["hs"] and not used["hs"]:
        relaxed.append("HS code")
    if full["origin"] and not used["origin"]:
        relaxed.append("excluded origin")

    start = as_of - timedelta(days=365)

    def sort_key(item):
        seller, rows, lane, listed = item
        window = [bill for bill in lane if bill.shipped and start <= bill.shipped <= as_of]
        preferred = {iso for iso, _name, _raw in parsed.prefers}
        preferred_bills = sum(1 for bill in rows if bill.origin in preferred)
        holds = bool(required) and all(code in seller.certs for code in required)
        value = sum(bill.value or 0 for bill in rows)
        # Destination in the year before the request dominates. Total volume is
        # only a small tie-break, so a large exporter of the code to other
        # countries does not outrank a smaller one who actually serves the lane.
        score = (
            len(window) * 10
            + len(lane) * 3
            + preferred_bills * 4
            + (30 if holds else 0)
            + (8 if listed else 0)
            + min(len(rows), 5)
        )
        return score, value, seller.entity_id

    ranked = sorted(chosen, key=lambda item: (-sort_key(item)[0], -sort_key(item)[1], sort_key(item)[2]))
    recommendations = []
    for index, item in enumerate(ranked, start=1):
        seller, rows, _lane, listed = item
        score, value, _entity = sort_key(item)
        recommendations.append({
            "rank": index,
            "entity_id": seller.entity_id,
            "name": seller.name,
            "activity_class": seller.activity,
            "score": score,
            "export_value_usd": round(value),
            "explanation": _explain(seller, rows, listed, parsed, as_of),
        })
    return {
        "candidate_count": len(ranked),
        "relaxed": relaxed,
        "recommendations": recommendations,
    }


def _parse_payload(rfq_id: str, parsed: ParsedRFQ) -> dict:
    categories: dict[str, dict] = {}
    seeks = []
    for product in parsed.products:
        if product.category:
            slot = categories.setdefault(product.category, {
                "phrases": [],
                "method": product.category_method or "text",
                "confidence": 0.9 if product.category_method == "text" else 0.85,
            })
            slot["phrases"].append(product.phrase)
            if product.category_method == "inherited_from_hs":
                slot["method"] = "inherited_from_hs"
        if product.hs_code:
            seeks.append({
                "rfq_id": rfq_id,
                "hs_code": product.hs_code,
                "method": "text",
                "confidence": product.hs_confidence,
            })
    return {
        "node": {
            "rfq_id": rfq_id,
            "product_phrase": parsed.product_phrase,
            "quantity": parsed.quantity,
            "incoterm": parsed.incoterm,
            "target_price_usd": parsed.target_price_usd,
            "parse_notes": " ".join(parsed.notes) or None,
        },
        "categories": [
            {
                "rfq_id": rfq_id,
                "category": name,
                "method": slot["method"],
                "confidence": slot["confidence"],
                "raw_text": " | ".join(slot["phrases"]),
            }
            for name, slot in categories.items()
        ],
        "seeks": seeks,
        "certs": [
            {"rfq_id": rfq_id, "code": code, "raw_text": raw}
            for code, raw in parsed.certs
        ],
        "prefers": [
            {"rfq_id": rfq_id, "iso2": iso, "raw_text": raw}
            for iso, _name, raw in parsed.prefers
        ],
        "excludes": [
            {"rfq_id": rfq_id, "iso2": iso, "raw_text": raw}
            for iso, _name, raw in parsed.excludes
        ],
        "deliver": (
            [{"rfq_id": rfq_id, "iso2": parsed.dest_iso, "raw_text": parsed.destination_raw}]
            if parsed.dest_iso else []
        ),
        "discharge": (
            [{"rfq_id": rfq_id, "port_id": parsed.port_id, "raw_text": parsed.destination_raw}]
            if parsed.port_id else []
        ),
    }


def _write(session, payloads: list[dict]) -> None:
    session.run(
        """
        MATCH (r:RFQ)-[rel:SEEKS|SEEKS_CATEGORY|REQUIRES|PREFERS_ORIGIN|EXCLUDES_ORIGIN|DELIVER_TO|DISCHARGE_AT]->()
        DELETE rel
        """
    ).consume()
    session.run(
        """
        UNWIND $rows AS row
        MATCH (r:RFQ {rfq_id: row.rfq_id})
        SET r.product_phrase = row.product_phrase,
            r.quantity = row.quantity,
            r.incoterm = row.incoterm,
            r.target_price_usd = row.target_price_usd,
            r.parse_notes = row.parse_notes
        """,
        rows=[payload["node"] for payload in payloads],
    ).consume()

    def link(query: str, key: str) -> None:
        rows = [row for payload in payloads for row in payload[key]]
        if rows:
            session.run(query, rows=rows).consume()

    link(
        """
        UNWIND $rows AS row
        MATCH (r:RFQ {rfq_id: row.rfq_id}), (c:Category {name: row.category})
        CREATE (r)-[:SEEKS_CATEGORY {method: row.method, confidence: row.confidence, raw_text: row.raw_text}]->(c)
        """,
        "categories",
    )
    link(
        """
        UNWIND $rows AS row
        MATCH (r:RFQ {rfq_id: row.rfq_id}), (h:HSCode {hs_code: row.hs_code})
        CREATE (r)-[:SEEKS {method: row.method, confidence: row.confidence}]->(h)
        """,
        "seeks",
    )
    link(
        """
        UNWIND $rows AS row
        MATCH (r:RFQ {rfq_id: row.rfq_id}), (c:Certification {code: row.code})
        CREATE (r)-[:REQUIRES {raw_text: row.raw_text}]->(c)
        """,
        "certs",
    )
    link(
        """
        UNWIND $rows AS row
        MATCH (r:RFQ {rfq_id: row.rfq_id}), (c:Country {iso2: row.iso2})
        CREATE (r)-[:PREFERS_ORIGIN {raw_text: row.raw_text}]->(c)
        """,
        "prefers",
    )
    link(
        """
        UNWIND $rows AS row
        MATCH (r:RFQ {rfq_id: row.rfq_id}), (c:Country {iso2: row.iso2})
        CREATE (r)-[:EXCLUDES_ORIGIN {raw_text: row.raw_text}]->(c)
        """,
        "excludes",
    )
    link(
        """
        UNWIND $rows AS row
        MATCH (r:RFQ {rfq_id: row.rfq_id}), (c:Country {iso2: row.iso2})
        CREATE (r)-[:DELIVER_TO {raw_text: row.raw_text}]->(c)
        """,
        "deliver",
    )
    link(
        """
        UNWIND $rows AS row
        MATCH (r:RFQ {rfq_id: row.rfq_id}), (p:Port {port_id: row.port_id})
        CREATE (r)-[:DISCHARGE_AT {raw_text: row.raw_text}]->(p)
        """,
        "discharge",
    )


def _parsed_view(parsed: ParsedRFQ) -> dict:
    return {
        "product_phrase": parsed.product_phrase,
        "quantity": parsed.quantity,
        "incoterm": parsed.incoterm,
        "target_price_usd": parsed.target_price_usd,
        "destination": parsed.destination_raw,
        "port": parsed.port_name,
        "country": parsed.dest_name,
        "products": [
            {
                "phrase": product.phrase,
                "quantity": product.quantity,
                "unit": product.unit,
                "category": product.category,
                "category_method": product.category_method,
                "hs_code": product.hs_code,
                "confidence": product.hs_confidence,
            }
            for product in parsed.products
        ],
        "prefers": [name for _iso, name, _raw in parsed.prefers],
        "excludes": [name for _iso, name, _raw in parsed.excludes],
        "certifications": [_CERT_NAME.get(code, code) for code, _raw in parsed.certs],
        "notes": parsed.notes,
    }


def main() -> None:
    load_env(ROOT)
    categories = load_hs_categories(ROOT / "hs_codes.csv")
    driver = open_database()
    try:
        with driver.session(database=database_name()) as session:
            sellers, rfqs, responders = _load_graph(session)
            payloads = []
            ranked = {}
            for rfq_id, row in rfqs.items():
                parsed = parse_rfq(row["text"], categories)
                payloads.append(_parse_payload(rfq_id, parsed))
                as_of = _as_date(row["created_at"])
                result = rank_sellers(parsed, sellers, row["buyer_id"], as_of, categories)
                result["buyer"] = row["buyer_name"]
                result["status"] = row["status"]
                result["parsed"] = _parsed_view(parsed)
                ranked[rfq_id] = result
            _write(session, payloads)
            counts = {
                record["rel"]: record["n"]
                for record in session.run(
                    """
                    MATCH (:RFQ)-[rel:SEEKS|SEEKS_CATEGORY|REQUIRES|PREFERS_ORIGIN|EXCLUDES_ORIGIN|DELIVER_TO|DISCHARGE_AT]->()
                    RETURN type(rel) AS rel, count(rel) AS n
                    """
                )
            }
    finally:
        driver.close()

    hits = 0
    reciprocal = 0.0
    evaluated = 0
    for rfq_id, responder_ids in responders.items():
        if not responder_ids or rfq_id not in ranked:
            continue
        evaluated += 1
        order = {row["entity_id"]: row["rank"] for row in ranked[rfq_id]["recommendations"]}
        best = min((order.get(entity_id) for entity_id in responder_ids if entity_id in order), default=None)
        if best is not None and best <= 10:
            hits += 1
        if best is not None:
            reciprocal += 1.0 / best
    evaluation = {
        "rfqs_with_a_response": evaluated,
        "hit_at_10": round(hits / evaluated, 3) if evaluated else None,
        "mrr": round(reciprocal / evaluated, 3) if evaluated else None,
        "responses_in_top_10": hits,
    }
    relaxed_counts: dict[str, int] = defaultdict(int)
    for result in ranked.values():
        relaxed_counts[", ".join(result["relaxed"]) or "none"] += 1

    show = []
    for rfq_id in POC_IDS:
        result = ranked[rfq_id]
        show.append({
            "rfq_id": rfq_id,
            "buyer": result["buyer"],
            "status": result["status"],
            "parsed": result["parsed"],
            "relaxed": result["relaxed"],
            "candidate_count": result["candidate_count"],
            "recommendations": result["recommendations"][:10],
        })
    report = {
        "rfqs_parsed": len(payloads),
        "relationship_counts": counts,
        "relaxation": dict(relaxed_counts),
        "evaluation": evaluation,
        "examples": show,
    }
    REPORT_PATH.parent.mkdir(exist_ok=True)
    REPORT_PATH.write_text(json.dumps(report, indent=2) + "\n")
    print(f"Wrote {REPORT_PATH.relative_to(ROOT)}")
    print("relationships", counts)
    print("evaluation", evaluation)
    print("relaxation", dict(relaxed_counts))
    for example in show:
        top = example["recommendations"][0] if example["recommendations"] else None
        print(example["rfq_id"], "candidates", example["candidate_count"], "relaxed", example["relaxed"])
        if top:
            print(" ", top["name"], top["explanation"])


if __name__ == "__main__":
    main()
