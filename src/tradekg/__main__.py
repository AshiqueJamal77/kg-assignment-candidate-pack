"""Clean the source files, resolve entities, and load the trade graph into Neo4j.

Run from the repository root, with Neo4j listening and `.env` filled in:

    PYTHONPATH=src python -m tradekg
"""

from __future__ import annotations

import json
import os
import time
from collections import Counter, defaultdict
from itertools import combinations
from pathlib import Path

import pandas as pd

from tradekg.classify import map_listing, resolve_shipment_hs
from tradekg.graph import (
    count_nodes,
    count_rels,
    insert_many,
    load_env,
    open_database,
    prepare_database,
)
from tradekg.normalize import blank_to_none, digits, parse_number
from tradekg.parties import PlatformIndex, off_platform_key, party_kind_and_name
from tradekg.reference import (
    all_certifications,
    all_countries,
    all_ports,
    all_units,
    canonical_unit,
    country_record,
    parse_certifications,
    port_record,
)
from tradekg.resolve import activity_class, resolve_companies, score_labels

ROOT = Path(__file__).resolve().parents[2]
REPORT_PATH = ROOT / "reports" / "task2_metrics.json"

NODE_LABELS = [
    "Country", "Port", "Unit", "Certification", "Category", "HSCode",
    "Company", "Registration", "Product", "Shipment", "RFQ", "Interaction",
]
REL_TYPES = [
    "HAS_REGISTRATION", "LOCATED_IN", "HOLDS", "OFFERS", "CLASSIFIED_AS",
    "IN_CATEGORY", "TRADED_IN", "PRICED_IN", "QUANTIFIED_IN", "SHIPPED",
    "CONSIGNED_TO", "ORIGINATED_IN", "DESTINED_FOR", "LOADED_AT",
    "DISCHARGED_AT", "IN_COUNTRY", "SAME_BILL", "POSTED", "PERFORMED",
    "DIRECTED_AT", "ABOUT_PRODUCT", "ABOUT_RFQ",
]


def _read_csv(name: str) -> pd.DataFrame:
    return pd.read_csv(ROOT / name, dtype=str, keep_default_na=False)


def _optional_number(value: str) -> float | None:
    return parse_number(value)


def _value_usd(value: str) -> float | None:
    number = parse_number(value)
    if number is None or number == 0:
        return None
    return number


def _most_common(values: list[str]) -> str:
    cleaned = [value.strip() for value in values if value and value.strip()]
    if not cleaned:
        return ""
    return Counter(cleaned).most_common(1)[0][0]


def main() -> None:
    started = time.time()
    load_env(ROOT)
    print("Reading source files")
    companies = _read_csv("companies.csv")
    products = _read_csv("products.csv")
    shipments = _read_csv("shipments.csv")
    interactions = _read_csv("interactions.csv")
    hs_codes = _read_csv("hs_codes.csv")
    labels = pd.read_csv(ROOT / "er_labels.csv")
    product_labels = pd.read_csv(ROOT / "product_hs_labels.csv", dtype=str)
    rfqs = json.loads((ROOT / "rfqs.json").read_text())

    print("Resolving platform companies")
    resolution = resolve_companies(companies)
    er_metrics = score_labels(resolution, labels)
    print(
        f"  entities {er_metrics['entities']}  "
        f"P {er_metrics['precision']:.3f}  R {er_metrics['recall']:.3f}  "
        f"F1 {er_metrics['f1']:.3f}"
    )

    print("Mapping product listings to HS codes")
    catalog = set(hs_codes["hs_code"])
    product_hs: dict[str, tuple[str | None, float, str]] = {}
    for row in products.itertuples(index=False):
        product_hs[row.product_id] = map_listing(row.title, row.description)
    correct = 0
    for row in product_labels.itertuples(index=False):
        predicted = product_hs[row.product_id][0] or "UNMAPPABLE"
        correct += int(predicted == row.hs_code)
    hs_accuracy = correct / len(product_labels)
    mapped_products = sum(1 for code, _, _ in product_hs.values() if code)
    print(f"  accuracy {correct}/{len(product_labels)} = {hs_accuracy:.3f}")

    listings_by_entity: Counter[str] = Counter()
    for row in products.itertuples(index=False):
        listings_by_entity[resolution.entity_of[row.company_id]] += 1
    for entity in resolution.entities:
        entity["activity_class"] = activity_class(
            entity["roles"],
            listings_by_entity[entity["entity_id"]] > 0,
        )

    print("Linking shipment parties")
    core_by_entity = {entity["entity_id"]: entity["cores"] for entity in resolution.entities}
    platform = PlatformIndex(resolution.entities, core_by_entity)
    party_cache: dict[tuple[str, str], tuple] = {}
    off_spellings: dict[tuple[str, str, str], list[str]] = defaultdict(list)

    def resolve_party(raw_name: str, raw_country: str) -> tuple[str, str, float, bool]:
        """Return entity key, method, confidence, and whether the key is already an id."""
        cache_key = (raw_name, raw_country)
        cached = party_cache.get(cache_key)
        if cached is not None:
            return cached
        kind, display = party_kind_and_name(raw_name)
        if kind == "company":
            entity_id, method, confidence = platform.match(raw_name, raw_country)
            if entity_id:
                result = (entity_id, method, confidence, True)
                party_cache[cache_key] = result
                return result
        key = off_platform_key(kind, display, raw_country)
        off_spellings[key].append(display)
        result = (key, "filed_name", 1.0, False)
        party_cache[cache_key] = result
        return result

    shipper_links = []
    consignee_links = []
    for row in shipments.itertuples(index=False):
        shipper_links.append(resolve_party(row.shipper_name, row.shipper_country))
        consignee_links.append(resolve_party(row.consignee_name, row.consignee_country))

    next_id = er_metrics["entities"] + 1
    off_ids: dict[tuple, str] = {}
    off_entities = []
    for key in sorted(off_spellings, key=lambda item: (item[0], item[2], item[1])):
        entity_id = f"ENT-{next_id:05d}"
        next_id += 1
        off_ids[key] = entity_id
        kind, _core, _iso = key
        off_entities.append({
            "entity_id": entity_id,
            "canonical_name": _most_common(off_spellings[key]),
            "on_platform": False,
            "party_kind": kind,
            "roles": [],
            "activity_class": "unknown",
            "year_established": None,
            "employee_range": None,
        })

    def entity_id_of(link: tuple) -> str:
        key, _method, _confidence, on_platform = link
        return key if on_platform else off_ids[key]

    kind_counts = Counter(entity["party_kind"] for entity in off_entities)
    on_platform_shippers = sum(1 for link in shipper_links if link[3])
    on_platform_consignees = sum(1 for link in consignee_links if link[3])
    print(
        f"  shippers on platform {on_platform_shippers}/{len(shipments)}  "
        f"consignees on platform {on_platform_consignees}/{len(shipments)}"
    )
    print(f"  off-platform parties {len(off_entities)}  {dict(kind_counts)}")

    _require_closed_vocab(companies, shipments)

    print("Loading graph into Neo4j")
    driver = open_database()
    try:
        prepare_database(driver)
        _load_reference(driver, hs_codes)
        _load_companies(driver, companies, resolution, off_entities)
        _load_products(driver, products, resolution, product_hs)
        _load_shipments(driver, shipments, catalog, shipper_links, consignee_links, entity_id_of)
        _load_rfqs(driver, rfqs, resolution)
        _load_interactions(driver, interactions, resolution)
        graph_counts = {
            "nodes": {label: count_nodes(driver, label) for label in NODE_LABELS},
            "relationships": {rel: count_rels(driver, rel) for rel in REL_TYPES},
        }
    finally:
        driver.close()
    elapsed = round(time.time() - started, 1)
    report = {
        "graph_store": "neo4j",
        "neo4j_uri": os.environ.get("NEO4J_URI", "bolt://localhost:7687"),
        "neo4j_database": os.environ.get("NEO4J_DATABASE", "neo4j"),
        "elapsed_seconds": elapsed,
        "entity_resolution": {
            "pairs": er_metrics["pairs"],
            "precision": round(er_metrics["precision"], 4),
            "recall": round(er_metrics["recall"], 4),
            "f1": round(er_metrics["f1"], 4),
            "tp": er_metrics["tp"],
            "fp": er_metrics["fp"],
            "fn": er_metrics["fn"],
            "tn": er_metrics["tn"],
            "registrations": er_metrics["registrations"],
            "entities": er_metrics["entities"],
            "cluster_size_histogram": {
                str(k): v for k, v in er_metrics["cluster_size_histogram"].items()
            },
        },
        "hs_mapping": {
            "labelled": int(len(product_labels)),
            "correct": correct,
            "accuracy": round(hs_accuracy, 4),
            "products": int(len(products)),
            "mapped": mapped_products,
            "unmappable": int(len(products) - mapped_products),
        },
        "shipment_parties": {
            "shipments": int(len(shipments)),
            "shipper_on_platform": on_platform_shippers,
            "shipper_off_platform": int(len(shipments) - on_platform_shippers),
            "consignee_on_platform": on_platform_consignees,
            "consignee_off_platform": int(len(shipments) - on_platform_consignees),
            "off_platform_parties": len(off_entities),
            "off_platform_by_kind": dict(Counter(e["party_kind"] for e in off_entities)),
        },
        "graph": graph_counts,
    }
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(json.dumps(report, indent=2) + "\n")
    print(f"Wrote {REPORT_PATH.relative_to(ROOT)} in {elapsed}s")
    print(
        "Graph loaded in Neo4j at "
        f"{os.environ.get('NEO4J_URI', 'bolt://localhost:7687')} "
        f"database {os.environ.get('NEO4J_DATABASE', 'neo4j')}"
    )


def _require_closed_vocab(companies: pd.DataFrame, shipments: pd.DataFrame) -> None:
    countries = set(companies["country"])
    for column in ("shipper_country", "consignee_country", "origin_country", "destination_country"):
        countries.update(shipments[column].unique())
    missing_countries = sorted(value for value in countries if value and country_record(value) is None)
    ports = set(shipments["port_of_loading"]) | set(shipments["port_of_discharge"])
    missing_ports = sorted(value for value in ports if value and port_record(value) is None)
    if missing_countries or missing_ports:
        raise SystemExit(f"Unmapped vocabulary countries={missing_countries} ports={missing_ports}")


def _load_reference(conn, hs_codes: pd.DataFrame) -> None:
    insert_many(conn, """
        CREATE (n:Country {iso2:$iso2, iso3:$iso3, name:$name, aliases:$aliases})
    """, all_countries())
    insert_many(conn, """
        CREATE (n:Port {port_id:$port_id, name:$name, unlocode:$unlocode, aliases:$aliases})
    """, [
        {"port_id": p["port_id"], "name": p["name"], "unlocode": p["unlocode"], "aliases": p["aliases"]}
        for p in all_ports()
    ])
    insert_many(conn, """
        CREATE (n:Unit {code:$code, dimension:$dimension, aliases:$aliases})
    """, all_units())
    insert_many(conn, """
        CREATE (n:Certification {code:$code, name:$name, family:$family, aliases:$aliases})
    """, all_certifications())
    categories = sorted(set(hs_codes["category"]))
    insert_many(conn, "CREATE (n:Category {name:$name})", [{"name": name} for name in categories])
    insert_many(conn, """
        CREATE (n:HSCode {hs_code:$hs_code, description:$description, chapter:$chapter})
    """, [
        {
            "hs_code": row.hs_code,
            "description": row.description,
            "chapter": row.hs_code[:2],
        }
        for row in hs_codes.itertuples(index=False)
    ])
    insert_many(conn, """
        MATCH (h:HSCode {hs_code:$hs_code}), (c:Category {name:$category})
        CREATE (h)-[:IN_CATEGORY]->(c)
    """, [
        {"hs_code": row.hs_code, "category": row.category}
        for row in hs_codes.itertuples(index=False)
    ])
    insert_many(conn, """
        MATCH (h:HSCode {hs_code:$hs_code}), (u:Unit {code:$unit})
        CREATE (h)-[:TRADED_IN]->(u)
    """, [
        {"hs_code": row.hs_code, "unit": canonical_unit(row.typical_unit)}
        for row in hs_codes.itertuples(index=False)
        if canonical_unit(row.typical_unit)
    ])
    insert_many(conn, """
        MATCH (p:Port {port_id:$port_id}), (c:Country {iso2:$iso2})
        CREATE (p)-[:IN_COUNTRY]->(c)
    """, [
        {"port_id": port["port_id"], "iso2": port["country_iso2"]}
        for port in all_ports()
    ])


def _load_companies(conn, companies: pd.DataFrame, resolution, off_entities: list[dict]) -> None:
    company_rows = []
    for entity in resolution.entities:
        company_rows.append({
            "entity_id": entity["entity_id"],
            "canonical_name": entity["canonical_name"],
            "on_platform": True,
            "party_kind": "company",
            "roles": entity["roles"],
            "activity_class": entity["activity_class"],
            "year_established": entity["year_established"],
            "employee_range": entity["employee_range"],
        })
    company_rows.extend(off_entities)
    insert_many(conn, """
        CREATE (n:Company {
            entity_id:$entity_id, canonical_name:$canonical_name,
            on_platform:$on_platform, party_kind:$party_kind, roles:$roles,
            activity_class:$activity_class, year_established:$year_established,
            employee_range:$employee_range})
    """, company_rows)

    by_id = {reg.company_id: reg for reg in resolution.registrations}
    registration_rows = []
    located_rows = []
    has_reg_rows = []
    holds_rows = []
    for row in companies.itertuples(index=False):
        reg = by_id[row.company_id]
        registration_rows.append({
            "company_id": reg.company_id,
            "raw_name": reg.raw_name,
            "raw_country": reg.raw_country,
            "city": reg.raw_city,
            "address": reg.raw_address,
            "website": reg.website,
            "email": blank_to_none(reg.email),
            "phone": reg.raw_phone,
            "website_host": reg.host or None,
            "phone_normalized": digits(reg.raw_phone or "") or None,
            "declared_type": reg.declared_type,
            "about": reg.about,
            "registered_on": reg.registered_on,
        })
        if reg.country_iso2:
            located_rows.append({
                "company_id": reg.company_id,
                "iso2": reg.country_iso2,
                "raw_country": reg.raw_country,
            })
        method, confidence = resolution.link_of[reg.company_id]
        has_reg_rows.append({
            "entity_id": resolution.entity_of[reg.company_id],
            "company_id": reg.company_id,
            "method": method,
            "confidence": confidence,
        })
        seen_certs = set()
        for code, fragment in parse_certifications(reg.certifications_raw or ""):
            if code in seen_certs:
                continue
            seen_certs.add(code)
            holds_rows.append({
                "entity_id": resolution.entity_of[reg.company_id],
                "code": code,
                "raw_text": fragment,
                "registration_id": reg.company_id,
            })
    insert_many(conn, """
        CREATE (n:Registration {
            company_id:$company_id, raw_name:$raw_name, raw_country:$raw_country,
            city:$city, address:$address, website:$website, email:$email,
            phone:$phone, website_host:$website_host, phone_normalized:$phone_normalized,
            declared_type:$declared_type, about:$about, registered_on:$registered_on})
    """, registration_rows)
    insert_many(conn, """
        MATCH (c:Company {entity_id:$entity_id}), (r:Registration {company_id:$company_id})
        CREATE (c)-[:HAS_REGISTRATION {method:$method, confidence:$confidence}]->(r)
    """, has_reg_rows)
    insert_many(conn, """
        MATCH (r:Registration {company_id:$company_id}), (c:Country {iso2:$iso2})
        CREATE (r)-[:LOCATED_IN {raw_country:$raw_country}]->(c)
    """, located_rows)
    insert_many(conn, """
        MATCH (c:Company {entity_id:$entity_id}), (cert:Certification {code:$code})
        CREATE (c)-[:HOLDS {raw_text:$raw_text, registration_id:$registration_id}]->(cert)
    """, holds_rows)


def _load_products(conn, products, resolution, product_hs) -> None:
    product_rows = []
    offers = []
    classified = []
    priced = []
    quantified = []
    for row in products.itertuples(index=False):
        code, confidence, method = product_hs[row.product_id]
        product_rows.append({
            "product_id": row.product_id,
            "registration_id": row.company_id,
            "title": row.title,
            "description": blank_to_none(row.description),
            "moq": _optional_number(row.moq),
            "price_usd_min": _optional_number(row.price_usd_min),
            "price_usd_max": _optional_number(row.price_usd_max),
            "listed_on": row.listed_on,
            "hs_status": "mapped" if code else "unmappable",
        })
        offers.append({
            "entity_id": resolution.entity_of[row.company_id],
            "product_id": row.product_id,
        })
        if code:
            classified.append({
                "product_id": row.product_id,
                "hs_code": code,
                "method": method,
                "confidence": confidence,
            })
        moq_unit = canonical_unit(row.moq_unit)
        if moq_unit:
            quantified.append({"product_id": row.product_id, "unit": moq_unit, "raw_unit": row.moq_unit})
        price_unit = canonical_unit(row.price_unit)
        if price_unit:
            priced.append({"product_id": row.product_id, "unit": price_unit})
    insert_many(conn, """
        CREATE (n:Product {
            product_id:$product_id, registration_id:$registration_id, title:$title,
            description:$description, moq:$moq, price_usd_min:$price_usd_min,
            price_usd_max:$price_usd_max, listed_on:$listed_on, hs_status:$hs_status})
    """, product_rows)
    insert_many(conn, """
        MATCH (c:Company {entity_id:$entity_id}), (p:Product {product_id:$product_id})
        CREATE (c)-[:OFFERS]->(p)
    """, offers)
    insert_many(conn, """
        MATCH (p:Product {product_id:$product_id}), (h:HSCode {hs_code:$hs_code})
        CREATE (p)-[:CLASSIFIED_AS {method:$method, confidence:$confidence, hs_raw:NULL}]->(h)
    """, classified)
    insert_many(conn, """
        MATCH (p:Product {product_id:$product_id}), (u:Unit {code:$unit})
        CREATE (p)-[:PRICED_IN]->(u)
    """, priced)
    insert_many(conn, """
        MATCH (p:Product {product_id:$product_id}), (u:Unit {code:$unit})
        CREATE (p)-[:QUANTIFIED_IN {raw_unit:$raw_unit}]->(u)
    """, quantified)


def _load_shipments(conn, shipments, catalog, shipper_links, consignee_links, entity_id_of) -> None:
    shipment_rows = []
    shipped = []
    consigned = []
    classified = []
    quantified = []
    originated = []
    destined = []
    loaded = []
    discharged = []
    bills: dict[str, list[str]] = defaultdict(list)
    for index, row in enumerate(shipments.itertuples(index=False)):
        unit = canonical_unit(row.quantity_unit)
        quantity = _optional_number(row.quantity)
        hs = resolve_shipment_hs(row.hs_code, catalog)
        shipment_rows.append({
            "shipment_id": row.shipment_id,
            "bill_of_lading": row.bill_of_lading,
            "shipment_date": row.shipment_date,
            "goods_description": row.goods_description,
            "hs_raw": row.hs_code,
            "quantity": quantity,
            "quantity_unit_raw": row.quantity_unit or None,
            "quantity_canonical": quantity if unit else None,
            "value_usd": _value_usd(row.value_usd),
            "incoterm": row.incoterm or None,
            "shipper_name_raw": row.shipper_name,
            "consignee_name_raw": row.consignee_name,
        })
        shipper = shipper_links[index]
        consignee = consignee_links[index]
        shipped.append({
            "entity_id": entity_id_of(shipper),
            "shipment_id": row.shipment_id,
            "raw_name": row.shipper_name,
            "raw_country": row.shipper_country,
            "method": shipper[1],
            "confidence": shipper[2],
        })
        consigned.append({
            "shipment_id": row.shipment_id,
            "entity_id": entity_id_of(consignee),
            "raw_name": row.consignee_name,
            "raw_country": row.consignee_country,
            "method": consignee[1],
            "confidence": consignee[2],
        })
        if hs:
            classified.append({
                "shipment_id": row.shipment_id,
                "hs_code": hs,
                "method": "digits",
                "confidence": 1.0,
                "hs_raw": row.hs_code,
            })
        if unit:
            quantified.append({
                "shipment_id": row.shipment_id,
                "unit": unit,
                "raw_unit": row.quantity_unit,
            })
        for column, bucket in (
            (row.origin_country, originated),
            (row.destination_country, destined),
        ):
            country = country_record(column)
            if country:
                bucket.append({
                    "shipment_id": row.shipment_id,
                    "iso2": country[0],
                    "raw_country": column,
                })
        for raw_port, bucket in (
            (row.port_of_loading, loaded),
            (row.port_of_discharge, discharged),
        ):
            port = port_record(raw_port)
            if port:
                bucket.append({
                    "shipment_id": row.shipment_id,
                    "port_id": port["port_id"],
                    "raw_port": raw_port,
                })
        if row.bill_of_lading:
            bills[row.bill_of_lading].append(row.shipment_id)
    same_bill = []
    for bill, ids in bills.items():
        if len(ids) < 2:
            continue
        ordered = sorted(ids)
        for left, right in combinations(ordered, 2):
            same_bill.append({"left": left, "right": right, "bill": bill})

    insert_many(conn, """
        CREATE (n:Shipment {
            shipment_id:$shipment_id, bill_of_lading:$bill_of_lading,
            shipment_date:$shipment_date, goods_description:$goods_description,
            hs_raw:$hs_raw, quantity:$quantity, quantity_unit_raw:$quantity_unit_raw,
            quantity_canonical:$quantity_canonical, value_usd:$value_usd,
            incoterm:$incoterm, shipper_name_raw:$shipper_name_raw,
            consignee_name_raw:$consignee_name_raw})
    """, shipment_rows)
    insert_many(conn, """
        MATCH (c:Company {entity_id:$entity_id}), (s:Shipment {shipment_id:$shipment_id})
        CREATE (c)-[:SHIPPED {raw_name:$raw_name, raw_country:$raw_country, method:$method, confidence:$confidence}]->(s)
    """, shipped)
    insert_many(conn, """
        MATCH (s:Shipment {shipment_id:$shipment_id}), (c:Company {entity_id:$entity_id})
        CREATE (s)-[:CONSIGNED_TO {raw_name:$raw_name, raw_country:$raw_country, method:$method, confidence:$confidence}]->(c)
    """, consigned)
    insert_many(conn, """
        MATCH (s:Shipment {shipment_id:$shipment_id}), (h:HSCode {hs_code:$hs_code})
        CREATE (s)-[:CLASSIFIED_AS {method:$method, confidence:$confidence, hs_raw:$hs_raw}]->(h)
    """, classified)
    insert_many(conn, """
        MATCH (s:Shipment {shipment_id:$shipment_id}), (u:Unit {code:$unit})
        CREATE (s)-[:QUANTIFIED_IN {raw_unit:$raw_unit}]->(u)
    """, quantified)
    insert_many(conn, """
        MATCH (s:Shipment {shipment_id:$shipment_id}), (c:Country {iso2:$iso2})
        CREATE (s)-[:ORIGINATED_IN {raw_country:$raw_country}]->(c)
    """, originated)
    insert_many(conn, """
        MATCH (s:Shipment {shipment_id:$shipment_id}), (c:Country {iso2:$iso2})
        CREATE (s)-[:DESTINED_FOR {raw_country:$raw_country}]->(c)
    """, destined)
    insert_many(conn, """
        MATCH (s:Shipment {shipment_id:$shipment_id}), (p:Port {port_id:$port_id})
        CREATE (s)-[:LOADED_AT {raw_port:$raw_port}]->(p)
    """, loaded)
    insert_many(conn, """
        MATCH (s:Shipment {shipment_id:$shipment_id}), (p:Port {port_id:$port_id})
        CREATE (s)-[:DISCHARGED_AT {raw_port:$raw_port}]->(p)
    """, discharged)
    insert_many(conn, """
        MATCH (a:Shipment {shipment_id:$left}), (b:Shipment {shipment_id:$right})
        CREATE (a)-[:SAME_BILL {bill_of_lading:$bill}]->(b)
    """, same_bill)


def _load_rfqs(conn, rfqs: list[dict], resolution) -> None:
    insert_many(conn, """
        CREATE (n:RFQ {rfq_id:$rfq_id, text:$text, created_at:$created_at, status:$status})
    """, [
        {
            "rfq_id": row["rfq_id"],
            "text": row["text"],
            "created_at": row["created_at"],
            "status": row["status"],
        }
        for row in rfqs
    ])
    insert_many(conn, """
        MATCH (c:Company {entity_id:$entity_id}), (r:RFQ {rfq_id:$rfq_id})
        CREATE (c)-[:POSTED]->(r)
    """, [
        {"entity_id": resolution.entity_of[row["buyer_company_id"]], "rfq_id": row["rfq_id"]}
        for row in rfqs
        if row["buyer_company_id"] in resolution.entity_of
    ])


def _load_interactions(conn, interactions, resolution) -> None:
    insert_many(conn, """
        CREATE (n:Interaction {event_id:$event_id, event_type:$event_type, event_time:$event_time})
    """, [
        {"event_id": row.event_id, "event_type": row.event_type, "event_time": row.event_time}
        for row in interactions.itertuples(index=False)
    ])
    performed = []
    directed = []
    about_product = []
    about_rfq = []
    for row in interactions.itertuples(index=False):
        actor = resolution.entity_of.get(row.actor_company_id)
        target = resolution.entity_of.get(row.target_company_id)
        if actor:
            performed.append({"entity_id": actor, "event_id": row.event_id})
        if target:
            directed.append({"event_id": row.event_id, "entity_id": target})
        if row.product_id:
            about_product.append({"event_id": row.event_id, "product_id": row.product_id})
        if row.rfq_id:
            about_rfq.append({"event_id": row.event_id, "rfq_id": row.rfq_id})
    insert_many(conn, """
        MATCH (c:Company {entity_id:$entity_id}), (e:Interaction {event_id:$event_id})
        CREATE (c)-[:PERFORMED]->(e)
    """, performed)
    insert_many(conn, """
        MATCH (e:Interaction {event_id:$event_id}), (c:Company {entity_id:$entity_id})
        CREATE (e)-[:DIRECTED_AT]->(c)
    """, directed)
    insert_many(conn, """
        MATCH (e:Interaction {event_id:$event_id}), (p:Product {product_id:$product_id})
        CREATE (e)-[:ABOUT_PRODUCT]->(p)
    """, about_product)
    insert_many(conn, """
        MATCH (e:Interaction {event_id:$event_id}), (r:RFQ {rfq_id:$rfq_id})
        CREATE (e)-[:ABOUT_RFQ]->(r)
    """, about_rfq)


if __name__ == "__main__":
    main()
