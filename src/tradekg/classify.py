"""Map a free-text product listing onto one of the 68 reference HS codes.

The catalogue is a few hundred repeated phrases, not open-ended prose. A
phrase table is enough, and it stays auditable: the relationship stores the
phrase that fired. Listings that never name a product
(``General merchandise``, ``Hot selling items``) are left unmapped. A 4-digit
heading is not guessed onto one of several 6-digit codes.

Rules are ordered. The first match wins, so ``broken rice`` is tested before
``rice`` and ``pickled coil`` before ``hot rolled coil``.
"""

from __future__ import annotations

import re

# (pattern, hs_code). First match wins.
_RULES: list[tuple[str, str]] = [
    (r"\b(broken rice|100%\s*broken)\b", "100640"),
    (r"\b(basmati|parboiled|jasmine|sona masoori|ir64|non basmati|long grain|white rice)\b|\brice\b", "100630"),
    (
        r"\b(tea bags|retail packs|packaged black tea|pouch)\b"
        r"|\btea\b.{0,24}\d+\s*g\b"
        r"|\d+\s*g\b.{0,24}\btea\b",
        "090230",
    ),
    (r"\b(black tea|ctc|bop|pf1|orthodox)\b", "090240"),
    (r"\b(roasted|espresso|medium roast)\b", "090121"),
    (r"\b(green coffee|unroasted|arabica|robusta)\b", "090111"),
    (r"\b(pandalus|cold[\s-]*water shrimp|northern prawns?)\b", "030616"),
    (r"\b(shrimp|prawns?|vannamei)\b", "030617"),
    (r"\b(in shell|unshelled|\brcn\b|raw cashew)\b", "080131"),
    (r"\bcashew\b", "080132"),
    (r"\b(crude palm|cpo)\b", "151110"),
    (r"\b(rbd|palm olein|refined palm|palm oil)\b", "151190"),
    (r"\b(raw cane|raw sugar|\bvhp\b|icumsa\s*600|icumsa\s*1200|brown raw)\b", "170114"),
    (r"\b(sugar|icumsa\s*45)\b", "170199"),
    (r"\bcombed\b", "520522"),
    (r"\b(carded|open end|cotton yarn|hosiery yarn)\b", "520512"),
    (r"\b(polyester|viscose|sublimation|dri-?fit)\b", "610990"),
    (r"\b(t-?shirts?|tees?)\b", "610910"),
    (
        r"\b(women|girls|ladies)\b.{0,40}\b(trousers?|shorts|jeans|pants|palazzo|capri)\b"
        r"|\b(trousers?|shorts|jeans|pants|palazzo|capri)\b.{0,40}\b(women|girls|ladies)\b",
        "620462",
    ),
    (
        r"\b(men|boys)\b.{0,40}\b(trousers?|shorts|jeans|pants|chino|denim|twill)\b"
        r"|\b(trousers?|shorts|jeans|pants|chino|denim)\b.{0,40}\b(men|boys)\b",
        "620342",
    ),
    (r"\b(bed linen|bed sheets?|duvet|pillow covers?|percale)\b", "630231"),
    (r"\b(towels?|terry)\b", "630260"),
    (r"\b(porcelain|vitrified|\bgvt\b|double charge)\b", "690721"),
    (r"\b(ceramic|semi-?vitreous)\b|\btiles?\b", "690722"),
    (r"\b(pickled|hrpo)\b", "720827"),
    (r"\b(hr coils?|hot rolled|hrc|sae\s*1006)\b", "720839"),
    (
        r"\b(ldpe|hdpe|\bpe\b|polyethylene|zip lock|garbage|shopping|carry)\b.{0,24}\bbags?\b"
        r"|\bbags?\b.{0,24}\b(ldpe|hdpe|polyethylene|zip)\b",
        "392321",
    ),
    (r"\b(lldpe|low density polyethylene|ldpe)\b", "390110"),
    (r"\b(hdpe|high density polyethylene)\b", "390120"),
    (r"\b(polyethylene terephthalate|\bpet\b)\b", "390761"),
    (
        r"\b(stainless|ss\s*30\d\s*l?|ss\s*316\s*l?)\b.{0,40}\b(pipes?|tubes?)\b"
        r"|\b(pipes?|tubes?)\b.{0,30}\bstainless\b",
        "730640",
    ),
    (r"\b(erw|gi pipes?|galvanized|ms round|black pipes?)\b", "730630"),
    (r"\b(tiffin|utensils?|dinner plates?|cookware|pressure cooker)\b", "732393"),
    (r"\b(alloy|adc\s*12|a356|6063|billets?)\b", "760120"),
    (r"\b(aluminium|aluminum)\b", "760110"),
    (
        r"\bleather\b.{0,40}\b(bags?|totes?|clutch|handbags?)\b"
        r"|\b(bags?|totes?|clutch|handbags?)\b.{0,40}\bleather\b",
        "420221",
    ),
    (
        r"\b(canvas|jute|\bpu\b)\b.{0,30}\b(bags?|totes?|handbags?)\b"
        r"|\b(bags?|totes?|handbags?)\b.{0,30}\b(canvas|jute|\bpu\b)\b",
        "420222",
    ),
    (r"\b(shoes?|loafers?|sandals?)\b", "640399"),
    (r"\b(tbr|truck tyres?|truck tires?|bus tyres?|radial truck)\b", "401120"),
    (r"\b(pcr|car tyres?|car tires?|passenger car|radial car|tyres?|tires?)\b", "401110"),
    (r"\b(clarithromycin|ceftriaxone|doxycycline|azithromycin)\b", "300420"),
    (r"\b(paracetamol|omeprazole|ibuprofen|metformin|atorvastatin)\b", "300490"),
    (r"\bmilk powder\b", "040221"),
    (r"\b(lipstick|lip gloss)\b", "330410"),
    (r"\bsoap\b", "340111"),
    (r"\b(serum|moisturis\w*|body lotion|face cream|sunscreen|skin brightening)\b", "330499"),
    (r"\b(bedside|wardrobes?|bedroom|wooden beds?)\b", "940350"),
    (r"\b(coffee tables?|cabinets?|sideboards?|dining tables?|wooden furniture)\b", "940360"),
    (r"\b(toys?|plush)\b", "950300"),
    (r"\b(brake pads?|brake calipers?|brake rotors?|brake discs?|brake shoes?|disc brake)\b", "870830"),
    (r"\b(radiator|suspension|spare parts?)\b", "870899"),
    (r"\b(air condition\w*|split ac|\bac\b)\b", "841510"),
    (r"\bpumps?\b", "841370"),
    (r"\b(laptops?|chromebooks?|notebook computers?)\b", "847130"),
    (r"\b(inverters?|chargers?|rectifiers?|\bups\b)\b", "850440"),
    (r"\b(mcc panels?|control panels?|distribution panels?|switchboards?|plc control)\b", "853710"),
    (r"\b(cables?|wires?)\b", "854449"),
    (r"\b(cement|\bopc\b)\b", "252329"),
    (r"\burea\b", "310210"),
    (r"\b(marble|travertine)\b", "680221"),
    (r"\bdiamonds?\b", "710239"),
    (r"\bsilver\b", "711311"),
    (r"\bgold\b", "711319"),
    (r"\b(cartons?|corrugated boxes|corrugated)\b", "481910"),
    (r"\b(lentils?|masoor)\b", "071340"),
    (r"\b(beef|buffalo meat)\b", "020230"),
    (r"\bpepper\b", "090411"),
    (r"\bturmeric\b", "091030"),
]

_COMPILED = [(re.compile(pattern, re.I), code) for pattern, code in _RULES]

_MARKETING = re.compile(
    r"\b(export quality|wholesale|premium|best price|high quality|bulk supply|"
    r"for export|oem available|private label available)\b",
    re.I,
)


def listing_text(title: str, description: str = "") -> str:
    """Title, then description, with the marketing wrapper removed.

    Text after a ``|`` is an origin claim (``Turkey Origin``), not the product.
    """
    title_text = str(title or "").split("|", 1)[0]
    body = f"{title_text} {description or ''}"
    body = _MARKETING.sub(" ", body)
    body = body.lower().replace("’", "'")
    body = re.sub(r"[^a-z0-9%/\.\-\s]", " ", body)
    return re.sub(r"\s+", " ", body).strip()


def map_listing(title: str, description: str = "") -> tuple[str | None, float, str]:
    """Return ``(hs_code or None, confidence, method)``.

    ``method`` is ``phrase`` when a rule matched and ``unmappable`` otherwise.
    """
    text = listing_text(title, description)
    if len(text) < 3:
        return None, 0.0, "unmappable"
    for pattern, code in _COMPILED:
        if pattern.search(text):
            return code, 0.93, "phrase"
    return None, 0.0, "unmappable"


def resolve_shipment_hs(raw: str, catalog: set[str]) -> str | None:
    """Resolve a filed code onto the 6-digit reference list.

    An 8-digit code keeps its first six digits when that code is in the
    catalogue. A dotted 6-digit code (``0306.17``) is punctuation, not a
    different length. 4-digit and 5-digit values are left unresolved: padding
    a missing leading zero, or picking one subheading under a heading, would
    invent a classification.
    """
    digits = re.sub(r"\D", "", str(raw or ""))
    if len(digits) == 6 and digits in catalog:
        return digits
    if len(digits) == 8 and digits[:6] in catalog:
        return digits[:6]
    return None
