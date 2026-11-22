"""Link shipment shippers and consignees to a Company.

A platform registration is used only when the normalized name is the same, or
the same aside from a typo, and a second candidate in that country is clearly
worse. A one-character substitution inside an otherwise identical name is not
treated as a typo: Hengcheng and Fengcheng are different companies. A short or
ambiguous name stays off the platform. ``HARBOR`` in the United States matches
several Harbor companies, and attaching the shipment to one of them would
invent a buyer.

Parties that match no registration are still companies. ``on_platform`` is
false. Banks, forwarders, and negotiable "to order" bills are companies of a
different ``party_kind``, so a recommendation can ignore them without dropping
the lane.
"""

from __future__ import annotations

import re
from collections import defaultdict

from rapidfuzz import fuzz

from tradekg.normalize import core_name, core_tokens, fold, strip_embedded_address
from tradekg.reference import country_record

_GOODS = {
    "food", "foods", "foodstuff", "steel", "textile", "textiles", "agro",
    "plastic", "plastics", "trading", "tyre", "tyres", "auto", "garment",
    "garments", "coffee", "tea", "rice", "sugar",
}


def party_kind_and_name(raw_name: str) -> tuple[str, str]:
    """Return ``(party_kind, display name)`` for one filed party string."""
    cleaned = strip_embedded_address(raw_name)
    folded = re.sub(r"\s+", " ", fold(cleaned).lower()).strip(" .")
    if re.fullmatch(r"to\s+order", folded):
        return "to_order", "To Order"
    if "to the order of" in folded or folded.startswith("to order of"):
        rest = re.sub(r"^to (the )?order of\s+", "", folded).strip(" .")
        if "bank" in rest:
            display = " ".join(word.capitalize() for word in rest.split())
            return "bank", display
        return "to_order", "To Order"
    tokens = set(core_tokens(cleaned))
    forwarder = (
        "forwarder" in tokens
        or "forwarders" in tokens
        or ("freight" in tokens)
        or ("shipping" in tokens and ("logistics" in tokens or "freight" in tokens))
        or ("shipping" in tokens and not (tokens & _GOODS))
        or ("logistics" in tokens and not (tokens & _GOODS))
    )
    if forwarder:
        return "forwarder", cleaned.strip(" .")
    return "company", cleaned.strip(" .")


def _compact(text: str) -> str:
    return text.replace(" ", "")


def _token_typo(left: str, right: str) -> bool:
    """True when two tokens differ by a typo, not by a substituted name.

    One inserted or deleted character, a doubled letter, a truncated tail,
    or two adjacent letters swapped. A same-length substitution
    (Hengcheng / Fengcheng, Tianfeng / Xinfeng) is rejected: that is how
    distinct companies in this file are spelled.
    """
    if left == right:
        return True
    short, long = (left, right) if len(left) <= len(right) else (right, left)
    if len(short) >= 4 and long.startswith(short) and 0 < len(long) - len(short) <= 3:
        return True
    if abs(len(left) - len(right)) == 1:
        longer, shorter = (left, right) if len(left) > len(right) else (right, left)
        return any(longer[:i] + longer[i + 1 :] == shorter for i in range(len(longer)))
    if len(left) == len(right) and len(left) >= 4:
        diffs = [i for i, (a, b) in enumerate(zip(left, right)) if a != b]
        return (
            len(diffs) == 2
            and diffs[1] == diffs[0] + 1
            and left[diffs[0]] == right[diffs[1]]
            and left[diffs[1]] == right[diffs[0]]
        )
    return False


def cores_compatible(left: str, right: str) -> bool:
    """Shipment core and registration core are the same name, typos aside."""
    if not left or not right:
        return False
    if _compact(left) == _compact(right):
        return True
    left_tokens = left.split()
    right_tokens = right.split()
    if abs(len(left_tokens) - len(right_tokens)) > 1:
        return False
    shorter, longer = (
        (left_tokens, right_tokens)
        if len(left_tokens) <= len(right_tokens)
        else (right_tokens, left_tokens)
    )
    used: set[int] = set()
    for token in shorter:
        match = next(
            (index for index, other in enumerate(longer) if index not in used and _token_typo(token, other)),
            None,
        )
        if match is None:
            return False
        used.add(match)
    if len(longer) == len(shorter):
        return True
    extra = next(token for index, token in enumerate(longer) if index not in used)
    return len(extra) <= 2


class PlatformIndex:
    """Registrations grouped so a shipment name does not scan every company."""

    def __init__(self, entities: list[dict], core_by_entity: dict[str, list[str]]):
        self.core_by_entity = core_by_entity
        self.exact: dict[tuple[str, str], set[str]] = defaultdict(set)
        self.by_token: dict[tuple[str, str], set[str]] = defaultdict(set)
        for entity in entities:
            iso = entity.get("country_iso2") or ""
            for core in entity.get("cores") or []:
                self.exact[(core, iso)].add(entity["entity_id"])
                for token in core.split():
                    if len(token) >= 4:
                        self.by_token[(token, iso)].add(entity["entity_id"])

    def match(self, raw_name: str, raw_country: str) -> tuple[str | None, str, float]:
        """Return ``(entity_id or None, method, confidence)``."""
        country = country_record(raw_country)
        iso = country[0] if country else ""
        core = core_name(raw_name, strip_address=True)
        if not core or not iso:
            return None, "unresolved", 0.0
        exact = self.exact.get((core, iso), set())
        if len(exact) == 1:
            return next(iter(exact)), "exact_name", 0.96
        if len(exact) > 1:
            return None, "ambiguous", 0.0
        tokens = [token for token in core.split() if len(token) >= 4]
        if not tokens:
            return None, "unresolved", 0.0
        candidates: set[str] = set()
        for token in tokens:
            candidates |= self.by_token.get((token, iso), set())
        scored: list[tuple[float, str]] = []
        for entity_id in candidates:
            best = 0.0
            compatible = False
            for known in self.core_by_entity.get(entity_id, []):
                score = fuzz.token_sort_ratio(core, known)
                if score > best:
                    best = score
                if score >= 94 and cores_compatible(core, known):
                    compatible = True
            if best >= 90 and compatible:
                scored.append((best, entity_id))
        if not scored:
            return None, "unresolved", 0.0
        scored.sort(reverse=True)
        best_score, best_id = scored[0]
        second = scored[1][0] if len(scored) > 1 else 0.0
        if best_score >= 94 and best_score - second >= 6:
            return best_id, "fuzzy_name", round(best_score / 100, 4)
        return None, "ambiguous" if second else "unresolved", 0.0


def off_platform_key(kind: str, display_name: str, raw_country: str) -> tuple[str, str, str]:
    """Identity of a shipment party that is not a platform registration."""
    country = country_record(raw_country)
    iso = country[0] if country else ""
    if kind == "to_order":
        return ("to_order", "to order", "")
    core = core_name(display_name, strip_address=True) or fold(display_name).lower()
    if kind == "bank":
        return ("bank", core, "")
    return (kind, core, iso)
