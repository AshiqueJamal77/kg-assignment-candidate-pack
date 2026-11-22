# B2B trade knowledge graph

Synthetic trade data for a platform where one real company can have several registrations, products are free text, and shipments name parties instead of company ids. The ontology is in [docs/01-ontology.md](docs/01-ontology.md). Ingestion, entity resolution, and HS mapping are in [docs/02-ingestion.md](docs/02-ingestion.md).

## Run the pipeline

Neo4j must already be running on `bolt://localhost:7687`. Copy `.env.example` to `.env` and set the password.

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
PYTHONPATH=src .venv/bin/python -m tradekg
```

That reads the CSVs and `rfqs.json` in this directory and loads them into the Neo4j database named in `.env`. It also writes `reports/task2_metrics.json`. Re-running the command replaces the previous load of this ontology. If the database contains any other label, the loader stops.

Browser: [http://localhost:7474](http://localhost:7474). User `neo4j`, password from `.env`.

```cypher
MATCH (c:Company)
RETURN c.on_platform, count(*)
```

## Task 2 results

Measured on the labelled files only. Those files are not lookup keys in the matcher.

| Check | Result |
|---|---|
| Company entity resolution, 200 pairs in `er_labels.csv` | Precision 1.00, recall 1.00, F1 1.00 (100 TP, 0 FP, 0 FN) |
| Product HS mapping, 100 rows in `product_hs_labels.csv` | Accuracy 1.00 (100 / 100) |
| Platform companies | 5,020 registrations → 4,208 companies. Largest cluster is 3. |
| Product listings | 5,262 mapped to a 6-digit code, 137 left unmappable |
| Shipments | 50,173. Every row has a shipper and a consignee. |
| Shipper rows linked to a platform company | 30,804 of 50,173. The other 19,369 rows point at an off-platform party. |
| Consignee rows linked to a platform company | 26,180 of 50,173. The other 23,993 rows point at an off-platform party. |

Off-platform parties are still `Company` nodes, with `on_platform = false`. There are 4,185 of those companies, plus 33 forwarders, 5 banks, and one `To Order` party. Banks, forwarders, and to-order bills are not treated as buyers or suppliers. The lane itself stays on the shipment.

Shipment HS codes are linked only when the filed digits resolve to one of the 68 reference codes. Blank, 4-digit, and 5-digit values (7,341 rows) get no `CLASSIFIED_AS` edge.

RFQ text is parsed into category, HS code, destination, certificate, and origin edges. The ranking is Task 4.

## Task 3 results

The four business queries, the assumptions, a sample of each result, and the server time are in [docs/03-queries.md](docs/03-queries.md). Re-run them with:

```bash
PYTHONPATH=src .venv/bin/python -m tradekg.queries
```

That refreshes `reports/task3_results.json`. On this machine the four queries returned in 8 ms, 31 ms, 211 ms, and 175 ms.

## Task 4 results

RFQ parsing and the seller ranking are in [docs/04-matching.md](docs/04-matching.md). Re-run with:

```bash
PYTHONPATH=src .venv/bin/python -m tradekg.match
```

All 500 requests are parsed onto the graph. On the 427 requests that received a response, 65.8% have a responding seller inside the top 10. The five POC requests, with the explanation for each recommended seller, are in the note.

## Task 5: sourcing assistant

The app is Streamlit. From this directory, with Neo4j running:

```bash
.venv/bin/pip install -r requirements.txt
PYTHONPATH=src .venv/bin/streamlit run app.py
```

Search, a supplier scorecard, a price comparison, and posting a request are four sections of the same app. They call `src/tradekg/assistant.py`. The POC test set is written by:

```bash
PYTHONPATH=src .venv/bin/python -m tradekg.poc
```

That refreshes `reports/task5_poc.md`. The design note is [docs/05-design.md](docs/05-design.md).

### Prompt design and guardrails

There is no model call, so there is no model prompt and the cost per query is $0. The buyer's sentence is read by the same phrase table that classifies listings, plus the closed lists of countries, ports, and certificates. A search sentence can also fill an origin, a destination, a container count, or a manufacturer filter when the RFQ templates left that field empty. It does not overwrite a field the template already filled, so posting one of the 500 requests produces the same parse as Task 4.

"From India" or "Saudi origin" on a search is a requirement: the seller needs a shipment of that HS code from that country. "Prefer India" on a posted request stays a boost, which is how Task 4 ranks. "No China origin" drops bills that originated in China. A seller who only lists the product, or whose bills of that code all originated in the excluded country, is left off the list. The page says how many were omitted. If a filter removes everyone, the page says which constraint was dropped and shows the previous list.

The ranker, the scorecard, and the prices are Cypher and the in-memory seller index built from Cypher. The sentence next to a seller is a template filled with those counts: the HS code, the country, the window, the port, the origin, the certificate. A certificate is shown only when the company has a `HOLDS` edge. A price is `value_usd` divided by quantity, after converting kilograms, metric tons, and grams into the HS code's typical unit. Pieces are not converted into kilograms. Listing prices are a separate table.

The correction form on a posted request offers the 68 HS codes, the 19 countries, and the certificate list. A code that is not in the graph is ignored. A request typed into the form is ranked in memory and is not stored as a new RFQ node.

A model added later would be allowed to rephrase the JSON already on the page. It would not be asked to supply a supplier, a price, or a certificate that the JSON does not contain.
