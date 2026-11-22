"""Sourcing assistant. Run with: streamlit run app.py

Numbers on the page are read from Neo4j. The text parser does not call a
language model. A corrected field is used only when it is one of the closed
codes already in the graph.
"""

from __future__ import annotations

import streamlit as st

from tradekg.assistant import Assistant, apply_corrections, certification_choices, country_choices
from tradekg.rfq_parse import parse_rfq

st.set_page_config(page_title="Trade sourcing assistant", layout="wide")


@st.cache_resource
def load_assistant() -> Assistant:
    return Assistant.load()


def show_parsed(parsed: dict) -> None:
    products = parsed.get("products") or []
    bits = []
    for product in products:
        code = product.get("hs_code") or "no HS code"
        bits.append(f"{product.get('phrase')} → {code} ({product.get('category') or 'no category'})")
    st.write("**Product.** " + ("; ".join(bits) if bits else "Nothing extracted."))
    destination = parsed.get("destination") or "not stated"
    port = f", port {parsed['port']}" if parsed.get("port") else ""
    st.write(f"**Destination.** {destination}{port}")
    st.write("**Preferred origin.** " + (", ".join(parsed.get("prefers") or []) or "not stated"))
    st.write("**Excluded origin.** " + (", ".join(parsed.get("excludes") or []) or "not stated"))
    st.write("**Certificates.** " + (", ".join(parsed.get("certifications") or []) or "not stated"))
    quantity = products[0].get("quantity") if products else None
    unit = products[0].get("unit") if products else None
    if quantity is not None:
        st.write(f"**Quantity.** {quantity:g} {unit or ''}".rstrip())


def show_recommendations(result: dict) -> None:
    relaxed = result.get("relaxed") or []
    if relaxed or result["candidate_count"] == 0:
        st.warning(result["message"])
    else:
        st.success(result["message"])
    st.caption(f"Ranked as of {result['as_of']}.")
    if not result["recommendations"]:
        return
    for row in result["recommendations"]:
        with st.container(border=True):
            st.markdown(f"**{row['rank']}. {row['name']}**  \n{row['activity_class'] or 'activity unknown'}")
            st.write(str(row["explanation"]).replace("$", r"\$"))
            products = row.get("products") or []
            if products:
                st.caption("Listings classified as this code: " + "; ".join(
                    f"{item['title']} ({item['hs_code']})" for item in products
                ))
            else:
                st.caption("No listing is classified as this code. The match is shipment evidence.")


def show_prices(prices: dict) -> None:
    if not prices:
        return
    st.subheader(f"Traded price, HS {prices['hs_code']}")
    st.caption(
        f"{prices['description']} Unit: USD per {prices['unit']}. "
        f"{prices['traded_bills']} bills. {prices['dropped_bills']} bills dropped because the unit "
        "is a different dimension and was not converted."
    )
    st.markdown("**By origin.** Shipment value divided by quantity, one figure per bill of lading.")
    if prices["by_origin"]:
        st.dataframe(prices["by_origin"], hide_index=True, width="stretch")
    else:
        st.write("No traded price in a comparable unit.")
    st.markdown("**By supplier.** Same traded prices, grouped by the shipper.")
    if prices["by_supplier"]:
        st.dataframe(prices["by_supplier"], hide_index=True, width="stretch")
    st.markdown("**Listing prices.** These are asking prices on the platform, not prices from shipments.")
    if prices["listings"]:
        st.dataframe(prices["listings"], hide_index=True, width="stretch")
    else:
        st.write("No platform listing is classified as this code.")


def page_search(assistant: Assistant) -> None:
    st.header("Search")
    st.write(
        "Type a sourcing request. The page extracts the product, HS code, origin, "
        "destination and certificates, then ranks platform sellers."
    )
    examples = [
        "Frozen vannamei shrimp suppliers from India that already ship to the United States",
        "HDPE pipe grade resin, Saudi origin, ISO 9001 certified supplier",
        "Brake pads manufacturer with IATF 16949, no China origin",
        "Porcelain floor tiles 600x600 for a project in Saudi Arabia, need suppliers with experience shipping to KSA",
        "Who sells 1121 basmati rice and what is the going price by origin?",
        "Pandalus borealis cold-water shrimp, frozen",
        "Radial car tyres 205/55R16, 2 x 40ft containers to Mombasa",
        "Compare prices for refined white sugar ICUMSA 45 across origins",
    ]
    choice = st.selectbox("Examples", ["(type your own)"] + examples)
    text = st.text_area(
        "Request",
        value="" if choice.startswith("(") else choice,
        height=100,
        key=f"search_box_{choice}",
    )
    if st.button("Search", type="primary") and text.strip():
        result = assistant.search(text.strip())
        show_parsed(result["parsed"])
        show_recommendations(result)
        if result.get("prices"):
            show_prices(result["prices"])


def page_scorecard(assistant: Assistant) -> None:
    st.header("Supplier scorecard")
    st.write("The card covers every registration of the resolved company.")
    company_id = st.text_input("Registration id", value="CMP-04013")
    if st.button("Open scorecard", type="primary") and company_id.strip():
        card = assistant.scorecard(company_id.strip())
        if card is None:
            st.warning(f"No registration {company_id.strip()} is in the graph.")
            return
        st.subheader(card["name"])
        st.caption(
            f"{card['entity_id']} · {card['activity_class']} · roles: {', '.join(card['roles']) or 'none'}"
            + (
                f" · shipments {card['exports']['first_date']} to {card['exports']['last_date']}"
                if card["exports"]["first_date"] else ""
            )
        )
        columns = st.columns(3)
        columns[0].metric("Export bills", card["exports"]["bills"])
        columns[1].metric("Export value", f"${card['exports']['value_usd']:,.0f}")
        columns[2].metric("Import bills", card["imports"]["bills"])
        st.markdown("**Risk flags**")
        for flag in card["risk_flags"]:
            st.write(flag.replace("$", r"\$"))
        st.markdown("**Registrations**")
        st.dataframe(card["registrations"], hide_index=True, width="stretch")
        st.markdown("**Certifications held**")
        if card["certifications"]:
            st.dataframe(card["certifications"], hide_index=True, width="stretch")
        else:
            st.write("None on the registrations.")
        left, right = st.columns(2)
        with left:
            st.markdown("**Export destinations**")
            st.dataframe(card["exports"]["destinations"], hide_index=True, width="stretch")
            st.markdown("**Export origins**")
            st.dataframe(card["exports"]["origins"], hide_index=True, width="stretch")
            st.markdown("**Buyers**")
            st.dataframe(card["exports"]["top_buyers"], hide_index=True, width="stretch")
        with right:
            st.markdown("**HS codes shipped**")
            st.dataframe(card["exports"]["hs_codes"], hide_index=True, width="stretch")
            if card["exports"]["unclassified_bills"]:
                st.caption(f"{card['exports']['unclassified_bills']} export bills have no HS code.")
            st.markdown("**Import origins**")
            st.dataframe(card["imports"]["origins"], hide_index=True, width="stretch")
            st.markdown("**Suppliers bought from**")
            st.dataframe(card["imports"]["suppliers"], hide_index=True, width="stretch")
        response = card["responsiveness"]
        st.markdown("**Platform responsiveness**")
        st.write(
            f"Chat requests received {response['chat_requests_received']}, "
            f"chats accepted {response['chat_accepted']}"
            + (f" (rate {response['chat_accept_rate']})" if response["chat_accept_rate"] is not None else "")
            + f". Quotations sent {response['quotations_sent']}, "
            f"accepted {response['quotations_accepted']}"
            + (f" (rate {response['quotation_accept_rate']})" if response["quotation_accept_rate"] is not None else "")
            + f". RFQ responses {response['rfq_responses']}."
        )


def page_prices(assistant: Assistant) -> None:
    st.header("Price comparison")
    text = st.text_input("Product", value="refined white sugar ICUMSA 45")
    if st.button("Compare prices", type="primary") and text.strip():
        parsed = parse_rfq(text.strip(), assistant.hs_category)
        code = next((product.hs_code for product in parsed.products if product.hs_code), None)
        if not code:
            st.warning("No catalogue HS code matches this wording. No price was computed.")
            return
        st.write(f"Read as HS {code}, {assistant.descriptions.get(code, '')}.")
        show_prices(assistant.prices(code))


def page_rfq(assistant: Assistant) -> None:
    st.header("Post a sourcing request")
    st.write("The parse is shown before any seller is listed. Edit a field if it is wrong, then match.")
    preset = st.selectbox(
        "Load a sample",
        ["(empty)"] + ["RFQ-0007", "RFQ-0027", "RFQ-0052", "RFQ-0257", "RFQ-0399"],
    )
    if st.session_state.get("rfq_preset") != preset:
        st.session_state["rfq_preset"] = preset
        st.session_state.pop("parsed_obj", None)
    default_text = ""
    if preset != "(empty)" and preset in assistant.rfqs:
        default_text = assistant.rfqs[preset]["text"]
    text = st.text_area("Request text", value=default_text, height=140, key=f"rfq_box_{preset}")
    if st.button("Parse", type="primary") and text.strip():
        parsed, _flags = assistant.parse(text.strip())
        st.session_state["rfq_text"] = text.strip()
        st.session_state["rfq_id"] = preset if preset != "(empty)" else None
        st.session_state["parsed_obj"] = parsed
    parsed = st.session_state.get("parsed_obj")
    if parsed is None:
        return
    st.subheader("Extracted fields")
    show_parsed({
        "products": [
            {
                "phrase": product.phrase,
                "hs_code": product.hs_code,
                "category": product.category,
                "quantity": product.quantity,
                "unit": product.unit,
            }
            for product in parsed.products
        ],
        "destination": parsed.dest_name,
        "port": parsed.port_name,
        "prefers": [name for _iso, name, _raw in parsed.prefers],
        "excludes": [name for _iso, name, _raw in parsed.excludes],
        "certifications": [code for code, _raw in parsed.certs],
    })
    countries = country_choices()
    country_ids = [iso for iso, _name in countries]
    certs = certification_choices()
    cert_ids = [code for code, _name in certs]
    hs_codes = sorted(assistant.hs_category)
    current_hs = parsed.products[0].hs_code if parsed.products and parsed.products[0].hs_code else hs_codes[0]
    with st.form("corrections"):
        phrase = st.text_input("Product phrase", value=parsed.products[0].phrase if parsed.products else "")
        hs_code = st.selectbox("HS code", hs_codes, index=hs_codes.index(current_hs) if current_hs in hs_codes else 0)
        quantity = st.text_input("Quantity", value="" if not parsed.products or parsed.products[0].quantity is None else str(parsed.products[0].quantity))
        destination = st.selectbox(
            "Destination country",
            [""] + country_ids,
            index=(country_ids.index(parsed.dest_iso) + 1) if parsed.dest_iso in country_ids else 0,
            format_func=lambda iso: "not stated" if iso == "" else dict(countries)[iso],
        )
        prefer = st.multiselect(
            "Preferred origins",
            country_ids,
            default=[iso for iso, _name, _raw in parsed.prefers if iso in country_ids],
            format_func=lambda iso: dict(countries)[iso],
        )
        exclude = st.multiselect(
            "Excluded origins",
            country_ids,
            default=[iso for iso, _name, _raw in parsed.excludes if iso in country_ids],
            format_func=lambda iso: dict(countries)[iso],
        )
        required = st.multiselect(
            "Certificates",
            cert_ids,
            default=[code for code, _raw in parsed.certs if code in cert_ids],
            format_func=lambda code: dict(certs)[code],
        )
        st.caption("The HS code is the first product. Leave it unchanged to keep every product in the request.")
        submitted = st.form_submit_button("Match using these fields")
    if submitted:
        corrected = apply_corrections(parsed, assistant.hs_category, {
            "phrase": phrase,
            "hs_code": hs_code,
            "quantity": quantity,
            "destination_iso": destination or None,
            "prefers": prefer,
            "excludes": exclude,
            "certifications": required,
        })
        when = assistant.as_of
        rfq_id = st.session_state.get("rfq_id")
        buyer_id = ""
        if rfq_id and rfq_id in assistant.rfqs:
            from tradekg.match import _as_date
            when = _as_date(assistant.rfqs[rfq_id]["created_at"]) or assistant.as_of
            buyer_id = assistant.rfqs[rfq_id]["buyer_id"]
        result = assistant.search(
            st.session_state.get("rfq_text", ""),
            parsed=corrected,
            flags={},
            as_of=when,
            buyer_id=buyer_id,
        )
        result["message"] = "Matched on the corrected fields. " + result["message"]
        show_recommendations(result)


def main() -> None:
    st.title("Trade sourcing assistant")
    st.caption(
        "No language model is called. Extraction uses the phrase table and the closed "
        "country, port and certificate lists. Every supplier, price and certificate is a "
        "graph read. Cost per query: $0."
    )
    assistant = load_assistant()
    page = st.sidebar.radio("Section", ["Search", "Scorecard", "Prices", "Post a request"])
    if page == "Search":
        page_search(assistant)
    elif page == "Scorecard":
        page_scorecard(assistant)
    elif page == "Prices":
        page_prices(assistant)
    else:
        page_rfq(assistant)


if __name__ == "__main__":
    main()
