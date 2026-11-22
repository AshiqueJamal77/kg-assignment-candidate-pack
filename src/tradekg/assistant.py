"""Sourcing assistant. Every number comes from the graph.

Free-text search reuses the RFQ parser, then fills origin, destination, and
quantity when the sentence is not one of the RFQ templates. Ranking is the
Task 4 ranker. A field the parser did not find is left empty. Nothing is
invented to fill it.

Search treats the last shipment date in the extract as "today", because the
file ends in September 2026. A posted RFQ that already exists is ranked as of
its own created_at.
"""

from __future__ import annotations

import csv
import copy
import re
import statistics
from datetime import date
from pathlib import Path

from tradekg.graph import database_name, load_env, open_database
from tradekg.match import _as_date, _load_graph, rank_sellers
from tradekg.reference import all_certifications, all_countries, country_record
from tradekg.rfq_parse import ParsedRFQ, ProductAsk, load_hs_categories, parse_rfq, resolve_place

ROOT = Path(__file__).resolve().parents[2]

# Mass factors relative to a kilogram. Carats are not converted into kilograms.
_TO_KG = {"KG": 1.0, "MT": 1000.0, "G": 0.001}

# Words a buyer uses for a country that are not already in the country aliases.
_ORIGIN_WORD = {
    "saudi": "SA",
    "indian": "IN",
    "chinese": "CN",
    "brazilian": "BR",
    "turkish": "TR",
    "egyptian": "EG",
    "vietnamese": "VN",
    "german": "DE",
    "malaysian": "MY",
    "indonesian": "ID",
    "pakistani": "PK",
    "bangladeshi": "BD",
    "kenyan": "KE",
    "italian": "IT",
    "british": "GB",
    "american": "US",
    "emirati": "AE",
}


def _country(iso: str) -> tuple[str, str, str] | None:
    return country_record(iso)


def _span_place(span: str):
    text = re.sub(r"^(the|a)\s+", "", span.strip(" .,;"), flags=re.I)
    text = " ".join(text.split()[:5])
    if not text:
        return None, None
    port, country = resolve_place(text)
    if port or country:
        return port, country
    token = text.split()[0].lower()
    iso = _ORIGIN_WORD.get(token)
    if iso:
        return None, _country(iso)
    return None, None


def enrich_search(text: str, parsed: ParsedRFQ) -> dict:
    """Fill origin and destination the RFQ templates do not mark.

    Returns flags the ranker does not know about. Preferred origin from a
    search sentence is required, not a boost: "from India" is a constraint.
    The RFQ wording "Prefer India" is left as a boost because enrich only
    runs when the parser found no origin.
    """
    flags = {
        "activity": None,
        "origin_required": False,
        "show_prices": bool(re.search(r"\bprices?\b|\bper\s+(kg|mt|ton)", text, re.I)),
    }
    if parsed.dest_iso is None and parsed.port_id is None:
        for pattern in (
            r"\bship(?:ping|s|ped)?\s+to\s+(?:the\s+)?([A-Za-z][^,.]{1,40})",
            r"\bto\s+(?:the\s+)?([A-Za-z][^,.]{1,40})",
            r"\bproject in\s+(?:the\s+)?([A-Za-z][^,.]{1,40})",
        ):
            match = re.search(pattern, text, re.I)
            if not match:
                continue
            port, country = _span_place(match.group(1))
            if not port and not country:
                continue
            parsed.destination_raw = match.group(1).strip()
            if port:
                parsed.port_id = port["port_id"]
                parsed.port_name = port["name"]
                parsed.dest_iso = port["country_iso2"]
                named = _country(port["country_iso2"])
                parsed.dest_name = named[2] if named else None
            elif country:
                parsed.dest_iso = country[0]
                parsed.dest_name = country[2]
            break

    if not parsed.prefers:
        spans = []
        from_match = re.search(
            r"\bfrom\s+(?:the\s+)?([A-Za-z][^,.]{2,40}?)(?:\s+that|\s+who|\s+which|,|\.|$)",
            text,
            re.I,
        )
        if from_match:
            spans.append(from_match.group(1))
        origin_match = re.search(r"\b([A-Za-z]{3,20})\s+origin\b", text, re.I)
        if origin_match and not re.search(rf"\bno\s+{origin_match.group(1)}\b", text, re.I):
            spans.append(origin_match.group(1))
        excluded = {iso for iso, _name, _raw in parsed.excludes}
        for span in spans:
            _port, country = _span_place(span)
            if country and country[0] not in excluded:
                parsed.prefers.append((country[0], country[2], span.strip()))
                flags["origin_required"] = True
                break

    if parsed.quantity is None and parsed.products:
        containers = re.search(r"(\d+)\s*x\s*(\d+)\s*ft", text, re.I)
        if containers:
            parsed.products[0].quantity = float(containers.group(1))
            parsed.products[0].quantity_raw = containers.group(0)
            parsed.notes.append(f"Quantity is {containers.group(0)}, a container count.")

    if re.search(r"\bmanufacturers?\b", text, re.I):
        flags["activity"] = "manufacturer"
    return flags


def _convert(quantity: float, unit: str, typical: str) -> float | None:
    if quantity is None or quantity <= 0:
        return None
    if unit == typical:
        return quantity
    if unit in _TO_KG and typical in _TO_KG:
        return quantity * _TO_KG[unit] / _TO_KG[typical]
    return None


def _median(values: list[float]) -> float | None:
    if not values:
        return None
    return statistics.median(values)


def _percentile(values: list[float], fraction: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    index = min(len(ordered) - 1, max(0, round(fraction * (len(ordered) - 1))))
    return ordered[index]


class Assistant:
    def __init__(self, sellers, rfqs, hs_category, descriptions, typical_units, as_of: date):
        self.sellers = sellers
        self.rfqs = rfqs
        self.hs_category = hs_category
        self.descriptions = descriptions
        self.typical_units = typical_units
        self.as_of = as_of

    @classmethod
    def load(cls) -> "Assistant":
        load_env(ROOT)
        hs_category = load_hs_categories(ROOT / "hs_codes.csv")
        descriptions = {}
        typical = {}
        with (ROOT / "hs_codes.csv").open(newline="") as handle:
            for row in csv.DictReader(handle):
                descriptions[row["hs_code"]] = row["description"]
                unit = row["typical_unit"].strip().upper()
                typical[row["hs_code"]] = unit
        driver = open_database()
        try:
            with driver.session(database=database_name()) as session:
                sellers, rfqs, _responders = _load_graph(session)
        finally:
            driver.close()
        shipped = [
            bill.shipped
            for seller in sellers.values()
            for bill in seller.bills
            if bill.shipped
        ]
        as_of = max(shipped) if shipped else date.today()
        return cls(sellers, rfqs, hs_category, descriptions, typical, as_of)

    def parse(self, text: str) -> tuple[ParsedRFQ, dict]:
        parsed = parse_rfq(text, self.hs_category)
        flags = enrich_search(text, parsed)
        return parsed, flags

    def search(
        self,
        text: str,
        parsed: ParsedRFQ | None = None,
        flags: dict | None = None,
        as_of: date | None = None,
        buyer_id: str = "",
    ) -> dict:
        if parsed is None or flags is None:
            parsed, flags = self.parse(text)
        when = as_of or self.as_of
        sought = {product.hs_code for product in parsed.products if product.hs_code}
        if not sought and not any(product.category for product in parsed.products):
            return {
                "parsed": _view(parsed),
                "flags": flags,
                "as_of": when.isoformat(),
                "message": "No product in the catalogue matches this wording. No seller was ranked.",
                "relaxed": [],
                "candidate_count": 0,
                "recommendations": [],
                "prices": None,
            }
        ranked = rank_sellers(parsed, self.sellers, buyer_id, when, self.hs_category)
        recommendations = ranked["recommendations"]
        relaxed = list(ranked["relaxed"])
        notes = []

        if flags.get("origin_required") and parsed.prefers:
            needed = {iso for iso, _name, _raw in parsed.prefers}
            origin_name = parsed.prefers[0][1]
            kept = []
            for row in recommendations:
                seller = self.sellers[row["entity_id"]]
                if any(bill.origin in needed and (not sought or bill.hs in sought) for bill in seller.bills):
                    kept.append(row)
            if kept:
                recommendations = kept
                notes.append(
                    f"Required origin {origin_name}: each seller has at least one shipment of this code from there."
                )
            else:
                relaxed.append("required origin")
                notes.append(
                    f"No seller has a shipment of this product from {origin_name}. "
                    "The list below drops that constraint."
                )

        if flags.get("activity") == "manufacturer":
            makers = [row for row in recommendations if row["activity_class"] in {"manufacturer", "mixed"}]
            if makers:
                recommendations = makers
                notes.append("Limited to manufacturers and companies that both manufacture and trade.")
            elif recommendations:
                relaxed.append("manufacturer")
                notes.append(
                    "No manufacturer survived the other constraints. "
                    "The list below includes other activity classes."
                )

        if parsed.excludes and sought:
            blocked = {iso for iso, _name, _raw in parsed.excludes}
            evidenced = []
            for row in recommendations:
                seller = self.sellers[row["entity_id"]]
                if any(bill.hs in sought and bill.origin not in blocked for bill in seller.bills):
                    evidenced.append(row)
            dropped = len(recommendations) - len(evidenced)
            if evidenced:
                recommendations = evidenced
                if dropped:
                    notes.append(
                        f"{dropped} sellers were omitted because they have no shipment of this code "
                        "from outside the excluded origin. A listing alone does not establish origin."
                    )
            elif recommendations:
                relaxed.append("shipment evidence outside the excluded origin")
                notes.append(
                    "No seller has a shipment of this code from outside the excluded origin. "
                    "The list below keeps sellers that only list the product."
                )

        top = recommendations[:10]
        for index, row in enumerate(top, start=1):
            row["rank"] = index
            row["products"] = self._products(row["entity_id"], sought)
        message = " ".join(notes) + f" {len(recommendations)} sellers remain." if notes else _match_message(parsed, relaxed, len(recommendations))
        if notes and any(item not in {"required origin", "manufacturer"} for item in relaxed):
            message = message + " " + _match_message(parsed, [item for item in relaxed if item not in {"required origin", "manufacturer"}], len(recommendations))
        prices = self.prices(next(iter(sought))) if flags.get("show_prices") and sought else None
        return {
            "parsed": _view(parsed),
            "flags": flags,
            "as_of": when.isoformat(),
            "message": message,
            "relaxed": relaxed,
            "candidate_count": len(recommendations),
            "recommendations": top,
            "prices": prices,
        }

    def _products(self, entity_id: str, hs_codes: set[str]) -> list[dict]:
        seller = self.sellers.get(entity_id)
        if seller is None:
            return []
        rows = []
        for title, code in seller.listings:
            if hs_codes and code not in hs_codes:
                continue
            rows.append({"title": title, "hs_code": code})
            if len(rows) == 3:
                break
        return rows

    def prices(self, hs_code: str) -> dict:
        typical = self.typical_units.get(hs_code, "KG")
        load_env(ROOT)
        driver = open_database()
        try:
            with driver.session(database=database_name()) as session:
                shipment_rows = list(session.run(
                    """
                    MATCH (h:HSCode {hs_code: $hs})<-[:CLASSIFIED_AS]-(s:Shipment)<-[:SHIPPED]-(seller:Company)
                    WHERE s.value_usd IS NOT NULL AND s.quantity_canonical IS NOT NULL
                      AND seller.party_kind = 'company'
                    MATCH (s)-[:QUANTIFIED_IN]->(u:Unit)
                    MATCH (s)-[:ORIGINATED_IN]->(o:Country)
                    RETURN seller.entity_id AS entity_id,
                           seller.canonical_name AS name,
                           seller.on_platform AS on_platform,
                           s.shipment_id AS shipment_id,
                           s.bill_of_lading AS bill,
                           s.value_usd AS value_usd,
                           s.quantity_canonical AS quantity,
                           u.code AS unit,
                           o.iso2 AS origin,
                           o.name AS origin_name
                    """,
                    hs=hs_code,
                ))
                listing_rows = list(session.run(
                    """
                    MATCH (h:HSCode {hs_code: $hs})<-[:CLASSIFIED_AS]-(p:Product)<-[:OFFERS]-(seller:Company)
                    WHERE seller.on_platform = true AND seller.party_kind = 'company'
                    OPTIONAL MATCH (p)-[:PRICED_IN]->(u:Unit)
                    RETURN seller.canonical_name AS name,
                           p.product_id AS product_id,
                           p.title AS title,
                           p.price_usd_min AS price_min,
                           p.price_usd_max AS price_max,
                           u.code AS unit
                    """,
                    hs=hs_code,
                ))
        finally:
            driver.close()

        seen: dict[tuple, dict] = {}
        dropped = 0
        for record in shipment_rows:
            key = (record["entity_id"], record["bill"] or record["shipment_id"])
            current = seen.get(key)
            if current is None or record["shipment_id"] < current["shipment_id"]:
                seen[key] = dict(record)
        by_origin: dict[str, list[float]] = {}
        origin_names = {}
        by_seller: dict[str, dict] = {}
        for record in seen.values():
            quantity = _convert(record["quantity"], record["unit"], typical)
            if quantity is None:
                dropped += 1
                continue
            price = record["value_usd"] / quantity
            by_origin.setdefault(record["origin"], []).append(price)
            origin_names[record["origin"]] = record["origin_name"]
            slot = by_seller.setdefault(record["entity_id"], {
                "name": record["name"],
                "on_platform": record["on_platform"],
                "prices": [],
            })
            slot["prices"].append(price)

        def band(prices: list[float]) -> dict:
            return {
                "bills": len(prices),
                "median_usd": round(_median(prices), 2),
                "p25_usd": round(_percentile(prices, 0.25), 2),
                "p75_usd": round(_percentile(prices, 0.75), 2),
            }

        origins = []
        for iso, prices in sorted(by_origin.items(), key=lambda item: -len(item[1])):
            origins.append({"origin": origin_names[iso], "iso2": iso, **band(prices)})
        suppliers = []
        for entity_id, slot in sorted(by_seller.items(), key=lambda item: -len(item[1]["prices"])):
            suppliers.append({
                "entity_id": entity_id,
                "name": slot["name"],
                "on_platform": slot["on_platform"],
                **band(slot["prices"]),
            })

        listings = []
        for record in listing_rows:
            unit = record["unit"]
            low = record["price_min"]
            high = record["price_max"]
            # Listing price is USD per source unit. Multiply by how many source
            # units sit in one typical unit. PCS and KG are not converted.
            factor = _convert(1.0, typical, unit) if unit else None
            listings.append({
                "name": record["name"],
                "title": record["title"],
                "unit": unit,
                "price_min_usd": low,
                "price_max_usd": high,
                "price_min_per_typical": None if factor is None or low is None else round(low * factor, 2),
                "price_max_per_typical": None if factor is None or high is None else round(high * factor, 2),
                "comparable": factor is not None,
            })
        return {
            "hs_code": hs_code,
            "description": self.descriptions.get(hs_code, ""),
            "unit": typical,
            "by_origin": origins,
            "by_supplier": suppliers[:15],
            "listings": listings[:15],
            "traded_bills": sum(len(prices) for prices in by_origin.values()),
            "dropped_bills": dropped,
        }

    def scorecard(self, company_id: str) -> dict | None:
        load_env(ROOT)
        driver = open_database()
        try:
            with driver.session(database=database_name()) as session:
                found = session.run(
                    """
                    MATCH (c:Company)-[:HAS_REGISTRATION]->(r:Registration {company_id: $company_id})
                    RETURN c.entity_id AS entity_id, c.canonical_name AS name,
                           c.activity_class AS activity, c.roles AS roles,
                           c.on_platform AS on_platform, c.year_established AS year_established
                    """,
                    company_id=company_id,
                ).single()
                if found is None:
                    return None
                entity_id = found["entity_id"]
                registrations = list(session.run(
                    """
                    MATCH (c:Company {entity_id: $entity_id})-[rel:HAS_REGISTRATION]->(r:Registration)
                    OPTIONAL MATCH (r)-[:LOCATED_IN]->(country:Country)
                    RETURN r.company_id AS company_id, r.raw_name AS raw_name, r.city AS city,
                           r.declared_type AS declared_type, country.name AS country,
                           rel.method AS method
                    ORDER BY r.company_id
                    """,
                    entity_id=entity_id,
                ))
                certs = list(session.run(
                    """
                    MATCH (c:Company {entity_id: $entity_id})-[rel:HOLDS]->(cert:Certification)
                    RETURN cert.code AS code, cert.name AS name, rel.raw_text AS raw_text
                    ORDER BY cert.code
                    """,
                    entity_id=entity_id,
                ))
                shipped = list(session.run(
                    """
                    MATCH (c:Company {entity_id: $entity_id})-[:SHIPPED]->(s:Shipment)-[:CONSIGNED_TO]->(b:Company)
                    OPTIONAL MATCH (s)-[:CLASSIFIED_AS]->(h:HSCode)
                    OPTIONAL MATCH (s)-[:ORIGINATED_IN]->(o:Country)
                    OPTIONAL MATCH (s)-[:DESTINED_FOR]->(d:Country)
                    RETURN s.shipment_id AS shipment_id, s.bill_of_lading AS bill,
                           s.shipment_date AS shipment_date, s.value_usd AS value_usd,
                           h.hs_code AS hs_code, o.name AS origin, d.name AS destination,
                           b.entity_id AS buyer_id, b.canonical_name AS buyer,
                           b.party_kind AS buyer_kind
                    """,
                    entity_id=entity_id,
                ))
                bought = list(session.run(
                    """
                    MATCH (s:Shipment)-[:CONSIGNED_TO]->(c:Company {entity_id: $entity_id})
                    MATCH (seller:Company)-[:SHIPPED]->(s)
                    OPTIONAL MATCH (s)-[:CLASSIFIED_AS]->(h:HSCode)
                    OPTIONAL MATCH (s)-[:ORIGINATED_IN]->(o:Country)
                    RETURN s.shipment_id AS shipment_id, s.bill_of_lading AS bill,
                           s.value_usd AS value_usd, h.hs_code AS hs_code,
                           o.name AS origin, seller.canonical_name AS seller,
                           seller.party_kind AS seller_kind
                    """,
                    entity_id=entity_id,
                ))
                response = session.run(
                    """
                    MATCH (c:Company {entity_id: $entity_id})
                    RETURN
                      size([(c)<-[:DIRECTED_AT]-(req:Interaction {event_type: 'chat_request'}) | req]) AS chat_requests,
                      size([(c)-[:PERFORMED]->(acc:Interaction {event_type: 'chat_accepted'}) | acc]) AS chat_accepted,
                      size([(c)-[:PERFORMED]->(sent:Interaction {event_type: 'quotation_sent'}) | sent]) AS quotations_sent,
                      size([(c)<-[:DIRECTED_AT]-(won:Interaction {event_type: 'quotation_accepted'}) | won]) AS quotations_accepted,
                      size([(c)-[:PERFORMED]->(rfq:Interaction {event_type: 'rfq_response'}) | rfq]) AS rfq_responses
                    """,
                    entity_id=entity_id,
                ).single()
        finally:
            driver.close()

        export_bills = _dedupe(shipped)
        import_bills = _dedupe(bought)
        export_dates = sorted(str(bill["shipment_date"]) for bill in export_bills if bill["shipment_date"])
        unclassified = sum(1 for bill in export_bills if not bill["hs_code"])
        company_buyers = [
            bill for bill in export_bills
            if bill["buyer_kind"] == "company" and bill["buyer_id"] != entity_id and bill["value_usd"]
        ]
        totals: dict[str, dict] = {}
        for bill in company_buyers:
            slot = totals.setdefault(bill["buyer_id"], {"name": bill["buyer"], "value": 0.0, "bills": 0})
            slot["value"] += bill["value_usd"]
            slot["bills"] += 1
        export_value = sum(slot["value"] for slot in totals.values())
        top = max(totals.values(), key=lambda slot: slot["value"]) if totals else None
        share = (top["value"] / export_value) if top and export_value else None
        flags = []
        if share is not None and share > 0.6:
            flags.append(
                f"Customer concentration: {top['name']} is {share:.0%} of export value "
                f"({top['bills']} bills, ${top['value']:,.0f} of ${export_value:,.0f})."
            )
        elif share is not None:
            flags.append(
                f"Customer concentration: largest buyer {top['name']} is {share:.0%} of export value. "
                "The 60% line is not crossed."
            )
        else:
            flags.append("Customer concentration: no valued shipment to a company buyer.")
        activity = found["activity"]
        if activity == "trader":
            flags.append("Trading versus manufacturing: trader. No manufacturing signal on the registrations or the listings.")
        elif activity == "manufacturer":
            flags.append("Trading versus manufacturing: manufacturer.")
        elif activity == "mixed":
            flags.append("Trading versus manufacturing: mixed. The registrations declare both manufacturing and trading.")
        else:
            flags.append("Trading versus manufacturing: unknown. The registrations do not say.")

        def rate(numerator: int, denominator: int) -> float | None:
            if not denominator:
                return None
            return round(numerator / denominator, 3)

        return {
            "company_id": company_id,
            "entity_id": entity_id,
            "name": found["name"],
            "activity_class": activity,
            "roles": list(found["roles"] or []),
            "on_platform": found["on_platform"],
            "year_established": found["year_established"],
            "registrations": [dict(row) for row in registrations],
            "certifications": [dict(row) for row in certs],
            "exports": {
                "bills": len(export_bills),
                "valued_bills": len(company_buyers),
                "value_usd": round(export_value),
                "first_date": export_dates[0] if export_dates else None,
                "last_date": export_dates[-1] if export_dates else None,
                "top_buyers": _top(totals, "value", 5),
                "destinations": _count(export_bills, "destination"),
                "origins": _count(export_bills, "origin"),
                "hs_codes": _count(export_bills, "hs_code"),
                "unclassified_bills": unclassified,
            },
            "imports": {
                "bills": len(import_bills),
                "value_usd": round(sum(bill["value_usd"] or 0 for bill in import_bills)),
                "suppliers": _count(import_bills, "seller"),
                "origins": _count(import_bills, "origin"),
                "hs_codes": _count(import_bills, "hs_code"),
            },
            "responsiveness": {
                "chat_requests_received": response["chat_requests"],
                "chat_accepted": response["chat_accepted"],
                "chat_accept_rate": rate(response["chat_accepted"], response["chat_requests"]),
                "quotations_sent": response["quotations_sent"],
                "quotations_accepted": response["quotations_accepted"],
                "quotation_accept_rate": rate(response["quotations_accepted"], response["quotations_sent"]),
                "rfq_responses": response["rfq_responses"],
            },
            "risk_flags": flags,
        }

    def post_rfq(self, text: str, rfq_id: str | None = None) -> dict:
        when = self.as_of
        buyer_id = ""
        if rfq_id and rfq_id in self.rfqs:
            when = _as_date(self.rfqs[rfq_id]["created_at"]) or self.as_of
            buyer_id = self.rfqs[rfq_id]["buyer_id"]
            parsed = parse_rfq(text, self.hs_category)
            flags = {"origin_required": False, "activity": None, "show_prices": False}
        else:
            parsed, flags = self.parse(text)
            flags = {**flags, "show_prices": False}
        result = self.search(text, parsed=parsed, flags=flags, as_of=when, buyer_id=buyer_id)
        result["rfq_id"] = rfq_id
        return result


def _dedupe(rows) -> list[dict]:
    grouped = {}
    for record in rows:
        key = record["bill"] or record["shipment_id"]
        current = grouped.get(key)
        if current is None or record["shipment_id"] < current["shipment_id"]:
            grouped[key] = dict(record)
    return list(grouped.values())


def _count(rows: list[dict], key: str, limit: int = 5) -> list[dict]:
    counts: dict[str, int] = {}
    for row in rows:
        value = row.get(key)
        if not value:
            continue
        counts[value] = counts.get(value, 0) + 1
    ordered = sorted(counts.items(), key=lambda item: (-item[1], item[0]))
    return [{"name": name, "bills": count} for name, count in ordered[:limit]]


def _top(totals: dict[str, dict], value_key: str, limit: int) -> list[dict]:
    ordered = sorted(totals.values(), key=lambda slot: -slot[value_key])
    return [
        {"name": slot["name"], "bills": slot["bills"], "value_usd": round(slot["value"])}
        for slot in ordered[:limit]
    ]


def _view(parsed: ParsedRFQ) -> dict:
    return {
        "products": [
            {
                "phrase": product.phrase,
                "hs_code": product.hs_code,
                "category": product.category,
                "quantity": product.quantity,
                "unit": product.unit,
                "confidence": product.hs_confidence,
            }
            for product in parsed.products
        ],
        "incoterm": parsed.incoterm,
        "destination": parsed.dest_name,
        "port": parsed.port_name,
        "prefers": [name for _iso, name, _raw in parsed.prefers],
        "excludes": [name for _iso, name, _raw in parsed.excludes],
        "certifications": [code for code, _raw in parsed.certs],
        "notes": parsed.notes,
    }


def _match_message(parsed: ParsedRFQ, relaxed: list[str], count: int) -> str:
    if count == 0:
        return "No platform seller matches, including after the constraints were relaxed."
    if not relaxed:
        return f"{count} sellers match the extracted constraints."
    dropped = ", ".join(relaxed)
    return f"Nothing matched every constraint. Relaxed: {dropped}. {count} sellers remain."


def apply_corrections(base: ParsedRFQ, hs_category: dict[str, str], corrections: dict) -> ParsedRFQ:
    """Apply the form. A changed HS code replaces the product list with that one code.

    Leaving the HS code on the first product keeps the other products, so a
    two-item request is not collapsed when the buyer only confirms the parse.
    """
    code = corrections.get("hs_code") or None
    first = base.products[0].hs_code if base.products else None
    if code != first:
        return parsed_from_corrections(base, hs_category, corrections)
    parsed = copy.deepcopy(base)
    parsed.notes.append("Ranked from the corrected fields.")
    if parsed.products:
        if corrections.get("phrase"):
            parsed.products[0].phrase = corrections["phrase"]
        quantity = _float_or_none(corrections.get("quantity"))
        if quantity is not None:
            parsed.products[0].quantity = quantity
    dest = corrections.get("destination_iso") or None
    if dest != base.dest_iso:
        parsed.port_id = None
        parsed.port_name = None
        parsed.dest_iso = None
        parsed.dest_name = None
        parsed.destination_raw = None
        if dest:
            country = _country(dest)
            if country:
                parsed.dest_iso = country[0]
                parsed.dest_name = country[2]
                parsed.destination_raw = country[2]
    parsed.prefers = []
    parsed.excludes = []
    parsed.certs = []
    for iso in corrections.get("prefers") or []:
        country = _country(iso)
        if country:
            parsed.prefers.append((country[0], country[2], "corrected"))
    for iso in corrections.get("excludes") or []:
        country = _country(iso)
        if country:
            parsed.excludes.append((country[0], country[2], "corrected"))
    known = {row["code"] for row in all_certifications()}
    for code_name in corrections.get("certifications") or []:
        if code_name in known:
            parsed.certs.append((code_name, "corrected"))
    return parsed


def parsed_from_corrections(base: ParsedRFQ, hs_category: dict[str, str], corrections: dict) -> ParsedRFQ:
    """Rebuild a parse from the fields the buyer edited. Unknown codes are refused."""
    code = corrections.get("hs_code") or None
    if code and code not in hs_category:
        code = None
    phrase = corrections.get("phrase") or (base.products[0].phrase if base.products else "")
    product = ProductAsk(
        phrase=phrase,
        quantity=_float_or_none(corrections.get("quantity")),
        unit=corrections.get("unit") or None,
        quantity_raw=None,
        category=hs_category.get(code) if code else None,
        category_method="text" if code else None,
        hs_code=code,
        hs_confidence=0.93 if code else 0.0,
        note="Corrected by the buyer.",
    )
    parsed = ParsedRFQ(products=[product], notes=["Ranked from the corrected fields."])
    parsed.incoterm = corrections.get("incoterm") or None
    dest = corrections.get("destination_iso") or None
    if dest:
        country = _country(dest)
        if country:
            parsed.dest_iso = country[0]
            parsed.dest_name = country[2]
            parsed.destination_raw = country[2]
    for iso in corrections.get("prefers") or []:
        country = _country(iso)
        if country:
            parsed.prefers.append((country[0], country[2], "corrected"))
    for iso in corrections.get("excludes") or []:
        country = _country(iso)
        if country:
            parsed.excludes.append((country[0], country[2], "corrected"))
    known = {row["code"] for row in all_certifications()}
    for code_name in corrections.get("certifications") or []:
        if code_name in known:
            parsed.certs.append((code_name, "corrected"))
    return parsed


def _float_or_none(value) -> float | None:
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def certification_choices() -> list[tuple[str, str]]:
    return [(row["code"], row["name"]) for row in all_certifications()]


def country_choices() -> list[tuple[str, str]]:
    return [(row["iso2"], row["name"]) for row in all_countries()]
