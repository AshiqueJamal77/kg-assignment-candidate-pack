"""Write the POC test-set output. The app calls the same functions.

    PYTHONPATH=src .venv/bin/python -m tradekg.poc
"""

from __future__ import annotations

from pathlib import Path

from tradekg.assistant import Assistant

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "reports" / "task5_poc.md"

SEARCHES = [
    ("Q1", "Frozen vannamei shrimp suppliers from India that already ship to the United States"),
    ("Q2", "HDPE pipe grade resin, Saudi origin, ISO 9001 certified supplier"),
    ("Q3", "Brake pads manufacturer with IATF 16949, no China origin"),
    ("Q4", "Porcelain floor tiles 600x600 for a project in Saudi Arabia, need suppliers with experience shipping to KSA"),
    ("Q5", "Who sells 1121 basmati rice and what is the going price by origin?"),
    ("Q6", "Pandalus borealis cold-water shrimp, frozen"),
    ("Q7", "Radial car tyres 205/55R16, 2 x 40ft containers to Mombasa"),
    ("Q8", "Compare prices for refined white sugar ICUMSA 45 across origins"),
]
RFQS = ["RFQ-0007", "RFQ-0027", "RFQ-0052", "RFQ-0257", "RFQ-0399"]
CARDS = ["CMP-04013", "CMP-00260", "CMP-04471"]


def _cell(value) -> str:
    return str(value if value is not None else "").replace("|", "/").replace("\n", " ")


def _rate(value) -> str:
    if value is None:
        return "not applicable"
    return str(value)


def _parsed_lines(parsed: dict) -> list[str]:
    lines = []
    for product in parsed.get("products") or []:
        lines.append(
            f"- Product: {product.get('phrase')} → HS {product.get('hs_code') or 'none'} "
            f"({product.get('category') or 'no category'}), "
            f"quantity {product.get('quantity')} {product.get('unit') or ''}".rstrip()
        )
    lines.append(f"- Destination: {parsed.get('destination') or 'not stated'}" + (f", port {parsed['port']}" if parsed.get("port") else ""))
    lines.append("- Preferred origin: " + (", ".join(parsed.get("prefers") or []) or "not stated"))
    lines.append("- Excluded origin: " + (", ".join(parsed.get("excludes") or []) or "not stated"))
    lines.append("- Certificates: " + (", ".join(parsed.get("certifications") or []) or "not stated"))
    return lines


def _recs(result: dict) -> list[str]:
    lines = [
        result["message"],
        f"Relaxed: {', '.join(result['relaxed']) or 'nothing'}. Ranked as of {result['as_of']}. "
        f"{result['candidate_count']} sellers in the set, {len(result['recommendations'])} shown.",
        "",
    ]
    if not result["recommendations"]:
        lines.append("No seller returned.")
        return lines
    for row in result["recommendations"]:
        products = row.get("products") or []
        listing = (
            "Listings: " + "; ".join(f"{item['title']} ({item['hs_code']})" for item in products)
            if products else
            "No listing is classified as this code."
        )
        lines.append(f"{row['rank']}. {row['name']} ({row['entity_id']}, {row['activity_class']})")
        lines.append(f"   {row['explanation']}")
        lines.append(f"   {listing}")
    return lines


def _prices(prices: dict | None) -> list[str]:
    if not prices:
        return []
    lines = [
        "",
        f"Traded unit price for HS {prices['hs_code']} ({prices['description']}), USD per {prices['unit']}. "
        f"{prices['traded_bills']} bills kept, {prices['dropped_bills']} dropped for a different dimension.",
        "",
        "By origin:",
        "",
        "| Origin | Bills | Median | P25 | P75 |",
        "| --- | ---: | ---: | ---: | ---: |",
    ]
    for row in prices["by_origin"]:
        lines.append(
            f"| {row['origin']} | {row['bills']} | {row['median_usd']} | {row['p25_usd']} | {row['p75_usd']} |"
        )
    if not prices["by_origin"]:
        lines.append("| none |  |  |  |  |")
    lines += [
        "",
        "By supplier (top 15 by bill count):",
        "",
        "| Supplier | On platform | Bills | Median | P25 | P75 |",
        "| --- | --- | ---: | ---: | ---: | ---: |",
    ]
    for row in prices["by_supplier"]:
        lines.append(
            f"| {row['name']} | {row['on_platform']} | {row['bills']} | {row['median_usd']} | {row['p25_usd']} | {row['p75_usd']} |"
        )
    lines += [
        "",
        "Listing prices, converted into the same unit when the dimension matches. These are asking prices, not shipment prices.",
        "",
        "| Seller | Title | Listed unit | Min | Max | Min per typical | Max per typical |",
        "| --- | --- | --- | ---: | ---: | ---: | ---: |",
    ]
    for row in prices["listings"]:
        lines.append(
            f"| {_cell(row['name'])} | {_cell(row['title'])} | {_cell(row['unit'])} | {row['price_min_usd']} | {row['price_max_usd']} | "
            f"{row['price_min_per_typical']} | {row['price_max_per_typical']} |"
        )
    if not prices["listings"]:
        lines.append("| none |  |  |  |  |  |  |")
    return lines


def _card(card: dict) -> list[str]:
    response = card["responsiveness"]
    lines = [
        f"### {card['company_id']} — {card['name']}",
        "",
        f"{card['entity_id']}. Activity {card['activity_class']}. Roles: {', '.join(card['roles']) or 'none'}. "
        f"On platform: {card['on_platform']}. Year established: {card['year_established']}.",
        f"Export bills {card['exports']['bills']} from {card['exports']['first_date']} to {card['exports']['last_date']}. "
        f"Valued company-buyer bills {card['exports']['valued_bills']}, ${card['exports']['value_usd']:,}. "
        f"Import bills {card['imports']['bills']}, ${card['imports']['value_usd']:,}.",
        "",
        "Risk flags:",
        "",
    ]
    for flag in card["risk_flags"]:
        lines.append(f"- {flag}")
    lines += ["", "Registrations:", "", "| Id | Name | City | Country | Declared type | Link method |", "| --- | --- | --- | --- | --- | --- |"]
    for row in card["registrations"]:
        lines.append(
            f"| {_cell(row['company_id'])} | {_cell(row['raw_name'])} | {_cell(row['city'])} | {_cell(row['country'])} | {_cell(row['declared_type'])} | {_cell(row['method'])} |"
        )
    lines += ["", "Certifications:", ""]
    if card["certifications"]:
        for row in card["certifications"]:
            lines.append(f"- {row['code']} ({row['name']}), raw text `{row['raw_text']}`")
    else:
        lines.append("- None.")
    lines += ["", "Export destinations:", ""]
    for row in card["exports"]["destinations"]:
        lines.append(f"- {row['name']}: {row['bills']} bills")
    lines.append("")
    lines.append("Export origins:")
    lines.append("")
    for row in card["exports"]["origins"]:
        lines.append(f"- {row['name']}: {row['bills']} bills")
    lines.append("")
    lines.append("Buyers by export value:")
    lines.append("")
    for row in card["exports"]["top_buyers"]:
        lines.append(f"- {row['name']}: {row['bills']} bills, ${row['value_usd']:,}")
    lines.append("")
    lines.append("HS codes shipped:")
    lines.append("")
    for row in card["exports"]["hs_codes"]:
        lines.append(f"- {row['name']}: {row['bills']} bills")
    if card["exports"]["unclassified_bills"]:
        lines.append(f"- No HS code: {card['exports']['unclassified_bills']} bills")
    lines += [
        "",
        "Import origins:",
        "",
    ]
    for row in card["imports"]["origins"]:
        lines.append(f"- {row['name']}: {row['bills']} bills")
    lines += ["", "Bought from:", ""]
    for row in card["imports"]["suppliers"]:
        lines.append(f"- {row['name']}: {row['bills']} bills")
    lines += [
        "",
        "Platform responsiveness. Chat accept rate is chats this company accepted divided by chat requests directed at it. "
        "Quotation accept rate is quotations accepted by the counterparty divided by quotations this company sent. "
        "RFQ responses are responses this company performed.",
        "",
        f"- Chat requests received: {response['chat_requests_received']}. Accepted: {response['chat_accepted']}. Rate: {_rate(response['chat_accept_rate'])}.",
        f"- Quotations sent: {response['quotations_sent']}. Accepted: {response['quotations_accepted']}. Rate: {_rate(response['quotation_accept_rate'])}.",
        f"- RFQ responses: {response['rfq_responses']}.",
        "",
    ]
    return lines


def main() -> None:
    assistant = Assistant.load()
    lines = [
        "# POC test set",
        "",
        "Produced by `PYTHONPATH=src python -m tradekg.poc`. The Streamlit app (`streamlit run app.py`) calls the same functions.",
        "",
        "No language model is called. Extraction is the phrase table plus the closed country, port, and certificate lists. "
        "A search sentence can also set a required origin or a manufacturer filter. Those filters only drop sellers the ranker already returned. "
        "Cost per query: $0.",
        "",
        f"Search is ranked as of {assistant.as_of.isoformat()}, the latest shipment date in the extract. "
        "A posted RFQ that already exists is ranked as of its own `created_at`, and the buyer who posted it is excluded.",
        "",
        "## Search",
        "",
    ]
    for label, text in SEARCHES:
        result = assistant.search(text)
        lines.append(f"### {label}")
        lines.append("")
        lines.append(text)
        lines.append("")
        lines.extend(_parsed_lines(result["parsed"]))
        lines.append("")
        lines.extend(_recs(result))
        lines.extend(_prices(result.get("prices")))
        lines.append("")
    lines += ["## Posted RFQs", ""]
    for rfq_id in RFQS:
        record = assistant.rfqs[rfq_id]
        result = assistant.post_rfq(record["text"], rfq_id)
        lines.append(f"### {rfq_id}")
        lines.append("")
        lines.append(record["text"])
        lines.append("")
        lines.append(f"Buyer excluded: {record['buyer_name']} ({record['buyer_id']}). Request date {record['created_at']}.")
        lines.append("")
        lines.extend(_parsed_lines(result["parsed"]))
        lines.append("")
        lines.extend(_recs(result))
        lines.append("")
    lines += ["## Scorecards", ""]
    for company_id in CARDS:
        card = assistant.scorecard(company_id)
        if card is None:
            lines.append(f"### {company_id}")
            lines.append("")
            lines.append("No registration with this id.")
            lines.append("")
            continue
        lines.extend(_card(card))
    OUT.parent.mkdir(exist_ok=True)
    OUT.write_text("\n".join(lines) + "\n")
    print(f"wrote {OUT}")


if __name__ == "__main__":
    main()
