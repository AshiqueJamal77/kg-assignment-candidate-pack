"""Load the resolved trade graph into local Neo4j.

Connection settings come from the environment, or from a `.env` file in the
repository root:

    NEO4J_URI=bolt://localhost:7687
    NEO4J_USER=neo4j
    NEO4J_PASSWORD=...
    NEO4J_DATABASE=neo4j

The loader wipes the target database only when it is empty or already holds
this ontology. Any other label stops the run.
"""

from __future__ import annotations

import os
import re
from pathlib import Path

from neo4j import GraphDatabase
from neo4j import Driver

_PARAM = re.compile(r"\$([A-Za-z_][A-Za-z0-9_]*)")

NODE_LABELS = [
    "Country", "Port", "Unit", "Certification", "Category", "HSCode",
    "Company", "Registration", "Product", "Shipment", "RFQ", "Interaction",
]

# Unique property for each node label. The constraint is also the lookup index
# used when relationships are matched.
_KEYS = {
    "Country": "iso2",
    "Port": "port_id",
    "Unit": "code",
    "Certification": "code",
    "Category": "name",
    "HSCode": "hs_code",
    "Company": "entity_id",
    "Registration": "company_id",
    "Product": "product_id",
    "Shipment": "shipment_id",
    "RFQ": "rfq_id",
    "Interaction": "event_id",
}

_EXTRA_INDEXES = [
    ("Shipment", "shipment_date"),
    ("Shipment", "bill_of_lading"),
    ("Shipment", "value_usd"),
]


def load_env(root: Path) -> None:
    """Fill unset variables from `.env`. A variable already in the environment wins."""
    path = root / ".env"
    if not path.exists():
        return
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip("'\""))


def open_database() -> Driver:
    uri = os.environ.get("NEO4J_URI", "bolt://localhost:7687")
    user = os.environ.get("NEO4J_USER", "neo4j")
    password = os.environ.get("NEO4J_PASSWORD", "")
    if not password:
        raise SystemExit(
            "Set NEO4J_PASSWORD in the environment or in .env. "
            "Neo4j is at bolt://localhost:7687."
        )
    driver = GraphDatabase.driver(uri, auth=(user, password))
    driver.verify_connectivity()
    return driver


def database_name() -> str:
    return os.environ.get("NEO4J_DATABASE", "neo4j")


def prepare_database(driver: Driver) -> None:
    """Clear a previous load of this graph and create uniqueness constraints."""
    name = database_name()
    with driver.session(database=name) as session:
        labels = session.run(
            "CALL db.labels() YIELD label RETURN collect(label) AS labels"
        ).single()["labels"]
        foreign = sorted(set(labels) - set(NODE_LABELS))
        if foreign:
            raise SystemExit(
                "Refusing to wipe Neo4j database "
                f"{name!r}: it contains labels that are not part of this graph: {foreign}"
            )
        session.run(
            "MATCH (n) CALL (n) { DETACH DELETE n } IN TRANSACTIONS OF 10000 ROWS"
        ).consume()
        for label, key in _KEYS.items():
            session.run(
                f"CREATE CONSTRAINT {label.lower()}_{key} IF NOT EXISTS "
                f"FOR (n:{label}) REQUIRE n.{key} IS UNIQUE"
            ).consume()
        for label, key in _EXTRA_INDEXES:
            session.run(
                f"CREATE INDEX {label.lower()}_{key} IF NOT EXISTS "
                f"FOR (n:{label}) ON (n.{key})"
            ).consume()


def _unwind(query: str) -> str:
    body = _PARAM.sub(r"row.\1", query.strip())
    return f"UNWIND $rows AS row\n{body}"


def insert_many(driver: Driver, query: str, rows: list[dict], chunk: int = 2000) -> None:
    if not rows:
        return
    statement = _unwind(query)
    name = database_name()

    def write(tx, batch: list[dict]) -> None:
        tx.run(statement, rows=batch).consume()

    with driver.session(database=name) as session:
        for start in range(0, len(rows), chunk):
            session.execute_write(write, rows[start : start + chunk])


def count_nodes(driver: Driver, label: str) -> int:
    with driver.session(database=database_name()) as session:
        record = session.run(f"MATCH (n:{label}) RETURN count(n) AS c").single()
        return int(record["c"])


def count_rels(driver: Driver, rel_type: str) -> int:
    with driver.session(database=database_name()) as session:
        record = session.run(f"MATCH ()-[r:{rel_type}]->() RETURN count(r) AS c").single()
        return int(record["c"])
