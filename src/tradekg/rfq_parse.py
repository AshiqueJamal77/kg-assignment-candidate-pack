"""Parse an RFQ into the fields the ontology stores as relationships.

The product words are read twice. A coarse family pattern chooses the
category. The listing phrase table chooses a 6-digit code. The code is kept
only when it sits inside that category. A code outside the family is recorded
in the notes and not linked. Quantity, incoterm, destination, certificates,
and preferred or excluded origins are read from the wording around the product.
"""

from __future__ import annotations

import csv
import re
from dataclasses import dataclass, field
from pathlib import Path

from tradekg.classify import map_listing
from tradekg.reference import canonical_unit, country_record, parse_certifications, port_record

# Coarse family, tested in order. Specific goods come before the word inside
# them: coffee tables before coffee, shopping bags before polyethylene.
_FAMILY: list[tuple[str, str]] = [
    (
        r"\b(coffee tables?|dining tables?|bedside|wardrobes?|wooden furniture|"
        r"wooden beds?|cabinets?|sideboards?)\b",
        "Consumer Goods",
    ),
    (
        r"\b(handbags?|totes?|clutch|loafers?|sandals?|shoes?|toys?|plush)\b",
        "Consumer Goods",
    ),
    (
        r"\b(ldpe|hdpe|\bpe\b|polyethylene|zip lock|garbage|shopping|carry)\b.{0,24}\bbags?\b"
        r"|\bbags?\b.{0,24}\b(ldpe|hdpe|polyethylene|zip|garbage|shopping)\b"
        r"|\b(cartons?|corrugated)\b",
        "Packaging",
    ),
    (
        r"\b(tea|rice|shrimp|prawns?|vannamei|pandalus|coffee|cashew|palm|"
        r"sugar|beef|buffalo|lentils?|masoor|turmeric|pepper|milk)\b",
        "Agriculture & Food",
    ),
    (r"\b(tyres?|tires?|pcr|tbr|brake pads?|brake rotors?|brake discs?|disc brake|calipers?)\b", "Automotive"),
    (
        r"\b(ibuprofen|paracetamol|omeprazole|metformin|atorvastatin|clarithromycin|"
        r"ceftriaxone|doxycycline|azithromycin|tablets?)\b",
        "Pharmaceuticals",
    ),
    (r"\b(cement|opc|marble|travertine|tiles?|porcelain|ceramic|vitrified|gvt)\b", "Construction Materials"),
    (
        r"\b(urea|soap|lipstick|lip gloss|sunscreen|lotion|serum|moisturis\w*|"
        r"ldpe|lldpe|hdpe|polyethylene|\bpet\b)\b",
        "Chemicals, Plastics & Personal Care",
    ),
    (
        r"\b(yarn|t-?shirts?|tees?|trousers?|jeans|pants|palazzo|towels?|terry|"
        r"bed sheets?|bed linen|pillow covers?|duvet)\b",
        "Textiles & Apparel",
    ),
    (
        r"\b(coils?|pipes?|tubes?|cookware|utensils?|aluminium|aluminum|ingots?|billets?)\b",
        "Metals",
    ),
    (
        r"\b(pumps?|laptops?|chromebooks?|notebook|inverters?|chargers?|cables?|"
        r"wires?|panels?|switchboards?)\b",
        "Machinery & Electrical",
    ),
    (r"\b(diamonds?|silver jewellery|gold jewellery|\bgold\b|\bsilver\b)\b", "Gems & Jewellery"),
]

_FAMILY_COMPILED = [(re.compile(pattern, re.I), name) for pattern, name in _FAMILY]

_INCOTERMS = "CIF|CFR|FOB|DAP|EXW|FCA|CIP|CPT"
_UNIT = (
    r"metric\s+tons?|square\s+met(?:er|re)s?|kilograms?|grams?|"
    r"kgs?|gms?|kg|mts?|tons?|pieces?|pcs|units?|pairs?|m2|sqm"
)
_QTY = r"\d[\d,]*(?:\.\d+)?(?:\s*x\s*\d+\s*ft\s*fcl)?"

# A delivery city that is not itself a port. The link is to the country.
_CITY_COUNTRY = {
    "abu dhabi": "AE",
    "ajman": "AE",
    "atlanta": "US",
    "bandung": "ID",
    "belo horizonte": "BR",
    "birmingham": "GB",
    "bradford": "GB",
    "dubai": "AE",
    "joburg": "ZA",
    "johannesburg": "ZA",
    "kuala lumpur": "MY",
    "london": "GB",
    "manchester": "GB",
    "nakuru": "KE",
    "narayanganj": "BD",
    "sharjah": "AE",
    "tenth of ramadan": "EG",
    "10th of ramadan": "EG",
    "canton": "CN",
    "carrara": "IT",
    "chicago": "US",
    "cologne": "DE",
    "dhaka": "BD",
    "faisalabad": "PK",
    "leicester": "GB",
    "miami": "US",
    "negombo": "LK",
    "pretoria": "ZA",
    "rajkot": "IN",
    "riyadh": "SA",
    "sialkot": "PK",
    "surat": "IN",
    "verona": "IT",
    "yiwu": "CN",
    "bursa": "TR",
    "stuttgart": "DE",
}

# Spellings that mean a port already in the vocabulary.
_CITY_PORT = {
    "nyc": "New York",
    "la": "Los Angeles",
    "al jubail": "Jubail",
    "medan": "Belawan",
    "pulau pinang": "Penang",
    "tg. priok": "Tanjung Priok",
    "jiddah": "Jeddah",
}


@dataclass
class ProductAsk:
    phrase: str
    quantity: float | None
    unit: str | None
    quantity_raw: str | None
    category: str | None
    category_method: str | None
    hs_code: str | None
    hs_confidence: float
    note: str = ""


@dataclass
class ParsedRFQ:
    products: list[ProductAsk] = field(default_factory=list)
    incoterm: str | None = None
    target_price_usd: float | None = None
    target_unit: str | None = None
    destination_raw: str | None = None
    port_id: str | None = None
    port_name: str | None = None
    dest_iso: str | None = None
    dest_name: str | None = None
    prefers: list[tuple[str, str, str]] = field(default_factory=list)
    excludes: list[tuple[str, str, str]] = field(default_factory=list)
    certs: list[tuple[str, str]] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)

    @property
    def product_phrase(self) -> str | None:
        phrases = [product.phrase for product in self.products if product.phrase]
        return "; ".join(phrases) or None

    @property
    def quantity(self) -> float | None:
        for product in self.products:
            if product.quantity is not None:
                return product.quantity
        return None


def load_hs_categories(path: Path) -> dict[str, str]:
    with path.open(newline="") as handle:
        return {row["hs_code"]: row["category"] for row in csv.DictReader(handle)}


def _family(phrase: str) -> str | None:
    for pattern, name in _FAMILY_COMPILED:
        if pattern.search(phrase):
            return name
    return None


def _classify_product(phrase: str, categories: dict[str, str]) -> ProductAsk:
    family = _family(phrase)
    code, confidence, method = map_listing(phrase)
    note = ""
    category = family
    category_method = "text" if family else None
    kept = code
    if code and family and categories.get(code) != family:
        kept = None
        confidence = 0.0
        note = (
            f"Phrase table suggested HS {code}, which is {categories.get(code)}. "
            f"The product words read as {family}, so the code was not linked."
        )
    elif code and not family:
        category = categories.get(code)
        category_method = "inherited_from_hs"
        note = "No family word matched. The category is the reference category of the phrase-table code."
    elif family and not code:
        note = "The product words name a category and not one HS code."
    return ProductAsk(
        phrase=phrase.strip(),
        quantity=None,
        unit=None,
        quantity_raw=None,
        category=category,
        category_method=category_method,
        hs_code=kept,
        hs_confidence=confidence if kept else 0.0,
        note=note,
    )


def _number(raw: str) -> float | None:
    text = raw.strip().lower()
    fcl = re.match(r"(\d[\d,]*)\s*x\s*\d+\s*ft\s*fcl", text, re.I)
    if fcl:
        return float(fcl.group(1).replace(",", ""))
    cleaned = raw.replace(",", "").strip()
    if not cleaned:
        return None
    try:
        return float(cleaned)
    except ValueError:
        return None


def _unit(raw: str | None, quantity_raw: str | None) -> str | None:
    blob = f"{quantity_raw or ''} {raw or ''}".lower()
    if re.search(r"\d+\s*ft\s*fcl", blob):
        return None
    if not raw:
        return None
    text = raw.lower().strip().rstrip(".")
    if "metric ton" in text or text in {"mt", "mts", "ton", "tons"}:
        return "MT"
    if "square met" in text or text in {"m2", "sqm", "sq.m"}:
        return "SQM"
    if text in {"gm", "gms", "gram", "grams"}:
        return "G"
    return canonical_unit(text)


def _clean_place(raw: str) -> str:
    text = raw.strip().strip(" .")
    text = re.split(
        r"\b(Supplier|Origin|Target|Shipment|Monthly|Trial|One-time|Quarterly|"
        r"Prompt|Please|Only|Prefer|pls|Need|Certs|Terms)\b",
        text,
        maxsplit=1,
        flags=re.I,
    )[0]
    text = re.sub(rf"\s*\(({_INCOTERMS})\)\s*$", "", text, flags=re.I).strip(" .")
    text = re.sub(rf"^(?:{_INCOTERMS})\s+", "", text, flags=re.I).strip()
    return text


def resolve_place(raw: str) -> tuple[dict | None, tuple[str, str, str] | None]:
    """Return (port record or None, country record or None)."""
    place = _clean_place(raw)
    if not place:
        return None, None
    port = port_record(place)
    if port:
        return port, country_record(port["country_iso2"])
    country = country_record(place)
    if country:
        return None, country
    lowered = place.lower()
    alias = _CITY_PORT.get(lowered)
    if alias:
        port = port_record(alias)
        if port:
            return port, country_record(port["country_iso2"])
    iso = _CITY_COUNTRY.get(lowered)
    if iso:
        return None, country_record(iso)
    # "Mombasa Port" is in the vocabulary; "Port Klang" too. Try without a trailing Port.
    trimmed = re.sub(r"\s+port$", "", lowered).strip()
    if trimmed != lowered:
        return resolve_place(trimmed)
    return None, None


def _countries_in(span: str) -> list[tuple[str, str, str]]:
    """Country mentions in a short origin span. Longest alias wins, no overlaps."""
    from tradekg.reference import all_countries

    found: list[tuple[int, int, tuple[str, str, str]]] = []
    folded = span
    aliases: list[tuple[str, tuple[str, str, str]]] = []
    for record in all_countries():
        country = (record["iso2"], record["iso3"], record["name"])
        for alias in record["aliases"]:
            if len(alias) < 4 and alias.lower() not in {"uk", "us", "uae", "ksa", "prc"}:
                continue
            aliases.append((alias, country))
    aliases.sort(key=lambda item: len(item[0]), reverse=True)
    occupied = [False] * (len(folded) + 1)
    for alias, country in aliases:
        for match in re.finditer(rf"\b{re.escape(alias)}\b", folded, flags=re.I):
            if any(occupied[match.start() : match.end()]):
                continue
            for index in range(match.start(), match.end()):
                occupied[index] = True
            found.append((match.start(), match.end(), country))
    found.sort()
    seen = set()
    ordered = []
    for _start, _end, country in found:
        if country[0] in seen:
            continue
        seen.add(country[0])
        ordered.append(country)
    return ordered


def _attach_quantity(product: ProductAsk, qty_raw: str | None, unit_raw: str | None) -> None:
    if not qty_raw:
        return
    product.quantity_raw = qty_raw.strip()
    product.quantity = _number(qty_raw)
    product.unit = _unit(unit_raw, qty_raw)
    if product.unit is None and re.search(r"\d+\s*ft\s*fcl", qty_raw, re.I):
        product.note = (product.note + " " if product.note else "") + "Quantity is a container count, not a catalogued unit."


def parse_rfq(text: str, categories: dict[str, str]) -> ParsedRFQ:
    parsed = ParsedRFQ()
    body = text.strip()

    price = re.search(rf"Target price USD\s+([\d.]+)\s+per\s+({_UNIT})", body, re.I)
    if price:
        parsed.target_price_usd = float(price.group(1))
        parsed.target_unit = _unit(price.group(2), None)

    items = _products(body, categories)
    parsed.products = items

    place_raw, incoterm = _destination(body)
    parsed.incoterm = incoterm
    parsed.destination_raw = place_raw
    if place_raw:
        port, country = resolve_place(place_raw)
        if port:
            parsed.port_id = port["port_id"]
            parsed.port_name = port["name"]
        if country:
            parsed.dest_iso = country[0]
            parsed.dest_name = country[2]
        elif port:
            parsed.dest_iso = port["country_iso2"]
            country = country_record(port["country_iso2"])
            parsed.dest_name = country[2] if country else None
        if not port and not country:
            parsed.notes.append(f"Delivery place {place_raw!r} is not a known port or country.")

    prefer_span = _prefer_span(body)
    exclude_span = _exclude_span(body)
    if prefer_span:
        for iso2, _iso3, name in _countries_in(prefer_span):
            parsed.prefers.append((iso2, name, prefer_span.strip()))
        if not parsed.prefers:
            parsed.notes.append(f"Preferred origin {prefer_span!r} did not match a country.")
    if exclude_span:
        for iso2, _iso3, name in _countries_in(exclude_span):
            parsed.excludes.append((iso2, name, exclude_span.strip()))
        if not parsed.excludes:
            parsed.notes.append(f"Excluded origin {exclude_span!r} did not match a country.")

    # A preferred country named again in the exclusion span is an exclusion.
    excluded = {iso for iso, _name, _raw in parsed.excludes}
    parsed.prefers = [row for row in parsed.prefers if row[0] not in excluded]

    for code, fragment in parse_certifications(body):
        parsed.certs.append((code, fragment))

    for product in items:
        if product.note:
            parsed.notes.append(f"{product.phrase}: {product.note}")
        if product.quantity is not None and product.unit is None and product.quantity_raw and "fcl" in product.quantity_raw.lower():
            parsed.notes.append(f"{product.phrase}: {product.quantity_raw} containers.")
    if len(items) > 1:
        parsed.notes.append("The request names more than one product. Each code that resolved is linked.")
    return parsed


def _products(body: str, categories: dict[str, str]) -> list[ProductAsk]:
    multi = re.search(r"two items:\s*(.*)", body, re.I | re.S)
    if multi:
        chunks = re.findall(r"\d\)\s*(.+?)(?=\s+\d\)|\s+Both\b|$)", multi.group(1), re.I | re.S)
        products = []
        for chunk in chunks:
            match = re.match(rf"(.+?)\s*[-–]\s*({_QTY})\s*({_UNIT})?", chunk.strip(), re.I)
            if not match:
                products.append(_classify_product(chunk.strip(" ."), categories))
                continue
            product = _classify_product(match.group(1), categories)
            _attach_quantity(product, match.group(2), match.group(3))
            products.append(product)
        return products

    structured = [
        re.compile(rf"price for\s+(.+?)\s+qty\s+({_QTY})(?:\s+({_UNIT}))?\s+delivery\s+", re.I),
        re.compile(rf"Requirement:\s*(.+?)\s*(?:\n|$)\s*Qty\s*-\s*({_QTY})(?:\s+({_UNIT}|\S+))?", re.I),
        re.compile(rf"looking for\s+(.+?)\.\s*Quantity:\s*({_QTY})(?:\s+({_UNIT}))?", re.I),
        re.compile(rf"imports\s+(.+?)\s+into\s+.+?\.\s*We need\s+({_QTY})(?:\s+({_UNIT}))?", re.I),
        re.compile(rf"Urgent!!\s*(.+?)\s+required,\s*({_QTY})(?:\s+({_UNIT}))?", re.I),
        re.compile(
            rf"^Need\s+(.+?)\s+({_QTY})(?:\s+({_UNIT}))?\s+(?:{_INCOTERMS})\s+",
            re.I,
        ),
    ]
    for pattern in structured:
        match = pattern.search(body)
        if not match:
            continue
        product = _classify_product(match.group(1), categories)
        unit = match.group(3) if match.lastindex and match.lastindex >= 3 else None
        _attach_quantity(product, match.group(2), unit)
        return [product]

    # Last resort: the first line, so the text is not silently dropped.
    phrase = body.split("\n", 1)[0][:180]
    return [_classify_product(phrase, categories)]


def _destination(body: str) -> tuple[str | None, str | None]:
    # "Tg. Priok" keeps its abbreviation. A sentence-ending period still stops the place.
    place = r"((?:Tg\.)?(?:[^.\n]|Tg\.)+?)"
    # Port line plus a Terms line, for the Requirement template.
    port = re.search(r"^Port\s*-\s*(.+)$", body, re.I | re.M)
    terms = re.search(rf"^Terms\s*-\s*({_INCOTERMS})\b", body, re.I | re.M)
    if port:
        return port.group(1).strip(), (terms.group(1).upper() if terms else None)

    delivery = re.search(rf"delivery\s+(.+?)\s*\(({_INCOTERMS})\)", body, re.I)
    if delivery:
        return delivery.group(1).strip(), delivery.group(2).upper()

    both = re.search(rf"Both\s+({_INCOTERMS})\s+{place}(?:\.|$)", body, re.I)
    if both:
        return both.group(2).strip(), both.group(1).upper()

    sentence = re.search(rf"Delivery\s+({_INCOTERMS})\s+{place}(?:\.|$)", body, re.I)
    if sentence:
        return sentence.group(2).strip(), sentence.group(1).upper()

    inline = re.search(rf"\b({_INCOTERMS})\s+{place}(?:\.|$)", body)
    if inline:
        return inline.group(2).strip(), inline.group(1).upper()
    return None, None


def _prefer_span(body: str) -> str | None:
    patterns = [
        r"Origin\s*-\s*Prefer\s+(.+?)\s+origin",
        r"Origin preferred:\s*([^\.\n]+)",
        r"Prefer\s+(.+?)\s+origin",
    ]
    for pattern in patterns:
        match = re.search(pattern, body, re.I)
        if match:
            return match.group(1)
    return None


def _exclude_span(body: str) -> str | None:
    # Stay inside one sentence so "Prefer Turkey origin. UAE origin not acceptable"
    # does not pull Turkey into the exclusion.
    patterns = [
        r"([A-Za-z][^.]{0,50}?)\s+origin not acceptable",
        r"\bNo\s+([^.]{1,40}?)\s+origin",
        r"Do not offer\s+([^.]{1,40}?)\s+origin",
    ]
    spans = []
    for pattern in patterns:
        spans.extend(match.group(1) for match in re.finditer(pattern, body, re.I))
    if not spans:
        return None
    return "; ".join(spans)
