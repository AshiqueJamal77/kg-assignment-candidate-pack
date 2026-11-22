# Take-Home Assignment: B2B Trade Knowledge Graph

Time allowed: 7 days. Expected effort: 14 to 16 hours.
Submit: a Git repository with a README, a design note of 1 to 2 pages, and a demo video of 5 minutes or less.

## Context

You are building the knowledge graph for a B2B trade platform. Buyers and sellers trade products across countries.

The raw data is messy:
- One company appears under several names.
- Products are described in free text.
- Shipments carry company names, not company IDs.

The graph must answer two business questions:
1. Who should this seller talk to next?
2. Who can supply what this buyer needs?

All data in this pack is synthetic. DATA_README.md describes every file.

## Data provided

| File | Rows | What it is |
|---|---|---|
| companies.csv | 5,020 | Companies registered on the platform. Contains duplicates. |
| products.csv | 5,399 | Seller product listings. Free text, no HS code. |
| shipments.csv | 50,173 | Import/export records, Oct 2024 to Sep 2026. |
| rfqs.json | 500 | Buyer requests for quotation, in free text. |
| interactions.csv | 26,041 | Platform events: views, chats, quotations, RFQ responses. |
| hs_codes.csv | 68 | HS code reference list, with a category for each code. |
| er_labels.csv | 200 | Labelled company pairs: same entity or not. |
| product_hs_labels.csv | 100 | Labelled products with their correct HS code. |
| POC_TEST_SET.md | | Queries, RFQs and companies to run through the Task 5 POC. |

## Task 1. Ontology design (required)

- Define node types, relationship types and key properties.
- At minimum, cover Company, Product, HSCode, Category, Country, Port, Shipment and RFQ.
- Decide whether Shipment is a node or an edge. Explain the trade-off.
- Include a schema diagram.

## Task 2. Ingestion and entity resolution (required)

- Build a pipeline that cleans the data and loads it into a graph database.
- Neo4j is preferred. Any graph store is accepted if you justify it.
- Resolve duplicate companies in companies.csv. Report precision, recall and F1 on er_labels.csv.
- Link shipment shippers and consignees to companies. Shipments also contain companies that are not on the platform. Decide how to represent them.
- Map products to HS codes from hs_codes.csv. Any method is allowed. Report accuracy on product_hs_labels.csv.

## Task 3. Business queries (required)

Write graph queries for the following:

a. For buyer X, find alternative suppliers of HS code Y, excluding origin country Z.
b. List the buyers that import category A but have never interacted with any seller on the platform.
c. List the sellers that send more than 60% of their export value to a single buyer.
d. Find the five companies most similar to company X by trade pattern.

For each query, show the query, a sample output, and its run time. State any assumption you make.

## Task 4. RFQ-to-seller matching (required)

- For a given RFQ, return the top 10 sellers ranked by fit.
- Parse the RFQ text first: product, quantity, destination, certifications, preferred and excluded origins.
- Every recommendation must include a short explanation that follows the graph path. Example: "Exported HS 870899 to the UAE 14 times in the last 12 months. Holds IATF 16949."
- Describe how you would evaluate the ranking offline.

## Task 5. AI sourcing assistant POC (required)

Build a working proof of concept of an AI sourcing assistant on top of your graph. The reference product is Made-in-China.com's SourcingAI (ai.made-in-china.com). Buyers describe what they need in plain language. The assistant returns matched suppliers, supplier checks and price comparisons.

Build these four features:

1. Natural-language search. A buyer types a request such as "brake pads with IATF 16949, no China origin". The POC extracts product, HS code, origin, destination and certifications. It returns ranked suppliers and their matching products.
2. Supplier scorecard. For any company, show trade history, buyers, destinations, origins, certifications, platform responsiveness and risk flags. The scorecard must cover all registrations of the same company. Risk flags must include customer concentration, and trading versus manufacturing.
3. Price comparison. For a product, show unit price by origin and by supplier from shipment data, next to listing prices. Normalise units first.
4. Post a sourcing request. A buyer pastes an RFQ. The POC parses it, shows the parsed fields for correction, and returns matched suppliers with explanations. You may reuse Task 4.

Rules:
- Every supplier, number and claim on screen must trace to the graph. The LLM may parse and phrase. It must not invent suppliers, prices or certifications.
- If nothing matches, say so. Then show the closest alternatives and what was relaxed.
- Any LLM provider or local model is allowed. State which one, and the cost per query.

Run the queries, RFQs and scorecards in POC_TEST_SET.md. Include the outputs in your submission.

Deliver:
- The running app. Any stack is fine: Streamlit, a web app, or an API with a simple UI.
- A demo video of 5 minutes or less.
- A short section in your README on the prompt design and the guardrails.

Bonus: image search, where a buyer uploads a product photo and gets matching products. Use your own sample images.

## Design note (required, 1 to 2 pages)

- How the system scales to 50 million nodes with daily incremental loads.
- How entity resolution stays correct as new data arrives.
- What you would build next, and why.
- What you skipped, and why.

## Evaluation

| Area | Weight |
|---|---|
| Ontology quality and reasoning | 15% |
| Entity resolution and HS mapping, with measured results | 20% |
| Query correctness and performance | 15% |
| RFQ matching quality and explainability | 15% |
| AI sourcing assistant POC | 25% |
| Design note: scale, trade-offs and judgment | 10% |

You may use LLMs. We judge whether the output is correct and measured, not whether an LLM was used.

