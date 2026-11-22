"""Resolve duplicate platform registrations into one Company.

The labelled pairs in er_labels.csv are an evaluation set. They are not
hard-coded and they are not blocking keys. A pair is predicted positive when
the two registrations land in the same connected component.

Links, in the order they are applied:

1. Phone. The last 8 digits match and the names are not unrelated. Phone
   collisions in this file are duplicate spellings, including typos
   (``spreme`` / ``supreme``, ``vianyak`` / ``vinayak``).
2. Corporate email, same city, names nearly equal, founding years both
   present and within a year. Free inboxes are shared by unrelated firms
   and are ignored. A blank year is not treated as a match.
3. Same normalized name and city, founding years both present and within
   a year, or both blank.
4. Same website host, same city, same year rule, and a similar name.
5. Corporate email domain matches the other row's website or email domain,
   same city, same year rule, similar name. This catches ``OH Agro``, whose
   site is ``omhanumanagro.in``.
6. Same street address and city, and the names still agree. Unrelated firms
   reuse street strings, so the name check is required.
7. An undated registration is attached only when every dated row in that
   same block (name, website, or email domain) was founded within a year
   of the others. A blank year must not bridge Oasis Commodities 1994 and
   Oasis Commodities 2003.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field

import pandas as pd
from rapidfuzz import fuzz

from tradekg.normalize import (
    address_key,
    blank_to_none,
    core_name,
    corporate_email_domain,
    email_address,
    email_domain,
    parse_year,
    phone_key,
    website_host,
)
from tradekg.reference import canonical_city, country_record, parse_certifications

_ROLE_PATTERNS = [
    ("manufacturer", ("manufactur",)),
    ("exporter", ("export",)),
    ("importer", ("import",)),
    ("trader", ("trad", "re-export", "reexport")),
    ("distributor", ("distribut",)),
    ("wholesaler", ("wholesal",)),
    ("buyer", ("buyer",)),
    ("retailer", ("retail",)),
]
_TRADER_ROLES = {"trader", "importer", "distributor", "wholesaler"}


@dataclass
class Registration:
    index: int
    company_id: str
    raw_name: str
    core: str
    country_iso2: str
    raw_country: str
    city: str
    raw_city: str
    address_key: str
    raw_address: str | None
    host: str
    email: str
    email_domain: str
    phone_key: str
    raw_phone: str | None
    declared_type: str
    roles: list[str]
    year: int | None
    employee_range: str | None
    certifications_raw: str | None
    cert_codes: list[str]
    about: str | None
    website: str | None
    registered_on: str
    richness: int = 0


@dataclass
class Link:
    left: int
    right: int
    method: str
    confidence: float


@dataclass
class Resolution:
    registrations: list[Registration]
    parent: list[int]
    links: list[Link]
    entity_of: dict[str, str] = field(default_factory=dict)
    link_of: dict[str, tuple[str, float]] = field(default_factory=dict)
    entities: list[dict] = field(default_factory=list)

    def find(self, index: int) -> int:
        parent = self.parent
        while parent[index] != index:
            parent[index] = parent[parent[index]]
            index = parent[index]
        return index

    def same(self, left: int, right: int) -> bool:
        return self.find(left) == self.find(right)

    def union(self, left: int, right: int, method: str, confidence: float) -> None:
        left_root = self.find(left)
        right_root = self.find(right)
        if left_root == right_root:
            return
        if left_root < right_root:
            self.parent[right_root] = left_root
        else:
            self.parent[left_root] = right_root
        self.links.append(Link(left, right, method, confidence))


def _roles(declared: str) -> list[str]:
    text = (declared or "").lower()
    found = [role for role, needles in _ROLE_PATTERNS if any(n in text for n in needles)]
    return found


def _richness(row: dict) -> int:
    score = 0
    for column, weight in (
        ("website", 3),
        ("email", 2),
        ("phone", 2),
        ("address", 1),
        ("year_established", 1),
        ("certifications", 1),
        ("about", 1),
        ("employee_range", 1),
    ):
        if blank_to_none(row.get(column)):
            score += weight
    return score


def _load(companies: pd.DataFrame) -> list[Registration]:
    rows: list[Registration] = []
    for index, row in enumerate(companies.itertuples(index=False)):
        raw = row._asdict()
        country = country_record(raw.get("country"))
        declared = blank_to_none(raw.get("company_type")) or ""
        website = blank_to_none(raw.get("website"))
        email = blank_to_none(raw.get("email"))
        phone = blank_to_none(raw.get("phone"))
        address = blank_to_none(raw.get("address"))
        cert_raw = blank_to_none(raw.get("certifications"))
        reg = Registration(
            index=index,
            company_id=str(raw["company_id"]),
            raw_name=str(raw["company_name"]),
            core=core_name(raw["company_name"]),
            country_iso2=country[0] if country else "",
            raw_country=str(raw.get("country") or ""),
            city=canonical_city(raw.get("city")),
            raw_city=str(raw.get("city") or ""),
            address_key=address_key(address or ""),
            raw_address=address,
            host=website_host(website or ""),
            email=email_address(email or ""),
            email_domain=corporate_email_domain(email or ""),
            phone_key=phone_key(phone or ""),
            raw_phone=phone,
            declared_type=declared,
            roles=_roles(declared),
            year=parse_year(raw.get("year_established")),
            employee_range=blank_to_none(raw.get("employee_range")),
            certifications_raw=cert_raw,
            cert_codes=[code for code, _fragment in parse_certifications(cert_raw or "")],
            about=blank_to_none(raw.get("about")),
            website=website,
            registered_on=str(raw.get("registered_on") or ""),
            richness=_richness(raw),
        )
        rows.append(reg)
    return rows


def _name_score(left: Registration, right: Registration) -> float:
    if not left.core or not right.core:
        return 0.0
    return max(
        fuzz.token_sort_ratio(left.core, right.core),
        fuzz.partial_ratio(left.core, right.core),
        fuzz.ratio(left.core, right.core),
    )


def _similar(left: Registration, right: Registration, threshold: float) -> bool:
    return _name_score(left, right) >= threshold


def _years_stated_and_close(left: Registration, right: Registration, slack: int = 1) -> bool:
    """Agreeing founding years, or both unknown.

    One dated row and one blank row are not treated as compatible. A blank
    year would otherwise bridge two dated companies that share a normalized
    name, such as Oasis Commodities 1994 and Oasis Commodities 2003.
    """
    if left.year is None or right.year is None:
        return left.year is None and right.year is None
    return abs(left.year - right.year) <= slack


def resolve_companies(companies: pd.DataFrame) -> Resolution:
    regs = _load(companies)
    resolved = Resolution(registrations=regs, parent=list(range(len(regs))), links=[])

    def group_pairs(key_fn, method: str, confidence: float, accept) -> None:
        groups: dict[str, list[int]] = defaultdict(list)
        for reg in regs:
            key = key_fn(reg)
            if key:
                groups[key].append(reg.index)
        for indexes in groups.values():
            if len(indexes) < 2:
                continue
            for i, left_index in enumerate(indexes):
                for right_index in indexes[i + 1 :]:
                    if accept(regs[left_index], regs[right_index]):
                        resolved.union(left_index, right_index, method, confidence)

    group_pairs(
        lambda reg: reg.phone_key,
        "phone",
        0.98,
        lambda a, b: _similar(a, b, 55),
    )
    # Exact email. Free inboxes (gmail, outlook, yahoo) are shared by unrelated
    # firms in this file, so only a corporate address counts, and only inside
    # one city with founding years that agree.
    group_pairs(
        lambda reg: (
            f"{reg.email}|{reg.city}|{reg.country_iso2}"
            if reg.email and email_domain(reg.email) not in {
                "gmail.com", "yahoo.com", "hotmail.com", "outlook.com", "live.com", "aol.com",
            }
            else ""
        ),
        "email",
        0.96,
        lambda a, b: _years_stated_and_close(a, b) and fuzz.token_sort_ratio(a.core, b.core) >= 90,
    )
    group_pairs(
        lambda reg: f"{reg.core}|{reg.city}|{reg.country_iso2}" if reg.core and reg.city else "",
        "name_city",
        0.90,
        _years_stated_and_close,
    )
    group_pairs(
        lambda reg: f"{reg.host}|{reg.city}|{reg.country_iso2}" if reg.host and reg.city else "",
        "website",
        0.93,
        lambda a, b: _years_stated_and_close(a, b) and _similar(a, b, 85),
    )

    # Email domain of one row equals the website host of another.
    by_domain_city: dict[str, list[int]] = defaultdict(list)
    for reg in regs:
        if reg.city and reg.country_iso2:
            if reg.host:
                by_domain_city[f"{reg.host}|{reg.city}|{reg.country_iso2}"].append(reg.index)
            if reg.email_domain:
                by_domain_city[f"{reg.email_domain}|{reg.city}|{reg.country_iso2}"].append(reg.index)
    seen_pairs: set[tuple[int, int]] = set()
    for indexes in by_domain_city.values():
        unique = list(dict.fromkeys(indexes))
        if len(unique) < 2:
            continue
        for i, left_index in enumerate(unique):
            for right_index in unique[i + 1 :]:
                pair = (left_index, right_index) if left_index < right_index else (right_index, left_index)
                if pair in seen_pairs:
                    continue
                seen_pairs.add(pair)
                left, right = regs[left_index], regs[right_index]
                cross = (
                    (left.email_domain and left.email_domain == right.host)
                    or (right.email_domain and right.email_domain == left.host)
                    or (left.email_domain and left.email_domain == right.email_domain)
                )
                if not cross:
                    continue
                if _years_stated_and_close(left, right) and _similar(left, right, 75):
                    resolved.union(left_index, right_index, "email_domain", 0.91)

    group_pairs(
        lambda reg: f"{reg.address_key}|{reg.city}|{reg.country_iso2}" if reg.address_key and reg.city else "",
        "address",
        0.94,
        lambda a, b: _similar(a, b, 80),
    )
    _link_undated(resolved, regs)
    _assign_entities(resolved)
    return resolved


def _shares_identifier(left: Registration, right: Registration) -> bool:
    if left.host and left.host == right.host:
        return True
    if left.email_domain and left.email_domain == right.email_domain:
        return True
    if left.address_key and left.address_key == right.address_key:
        return True
    return False


def _token_subset(left: Registration, right: Registration) -> bool:
    left_tokens = set(left.core.split())
    right_tokens = set(right.core.split())
    if len(left_tokens) < 2 or len(right_tokens) < 2:
        return False
    return left_tokens <= right_tokens or right_tokens <= left_tokens


def _link_undated(resolved: Resolution, regs: list[Registration]) -> None:
    """Attach an undated registration when the dated rows in its block agree.

    Used for duplicates where one profile left `year_established` blank.
    The attachment is refused when the block already contains founding years
    more than a year apart, because that block is two companies, not one.
    """

    def span_ok(indexes: list[int]) -> bool:
        years = [regs[i].year for i in indexes if regs[i].year is not None]
        return not years or max(years) - min(years) <= 1

    def run(key_fn, method: str, confidence: float, accept) -> None:
        groups: dict[str, list[int]] = defaultdict(list)
        for reg in regs:
            key = key_fn(reg)
            if key:
                groups[key].append(reg.index)
        for indexes in groups.values():
            if len(indexes) < 2 or not span_ok(indexes):
                continue
            dated = [i for i in indexes if regs[i].year is not None]
            undated = [i for i in indexes if regs[i].year is None]
            if not dated or not undated:
                continue
            for index in undated:
                for dated_index in dated:
                    if accept(regs[index], regs[dated_index]):
                        resolved.union(index, dated_index, method, confidence)
                        break

    run(
        lambda reg: f"{reg.core}|{reg.city}|{reg.country_iso2}" if reg.core and reg.city else "",
        "name_city",
        0.88,
        lambda undated, dated: len(undated.core.split()) >= 3 or _shares_identifier(undated, dated),
    )
    run(
        lambda reg: f"{reg.host}|{reg.city}|{reg.country_iso2}" if reg.host and reg.city else "",
        "website",
        0.90,
        lambda undated, dated: _similar(undated, dated, 85),
    )
    run(
        lambda reg: (
            f"{reg.email_domain}|{reg.city}|{reg.country_iso2}" if reg.email_domain and reg.city else ""
        ),
        "email_domain",
        0.89,
        lambda undated, dated: _similar(undated, dated, 80) or _token_subset(undated, dated),
    )


def _assign_entities(resolved: Resolution) -> None:
    clusters: dict[int, list[Registration]] = defaultdict(list)
    for reg in resolved.registrations:
        clusters[resolved.find(reg.index)].append(reg)

    # Evidence that attached a registration to something else. Singletons
    # have no link; confidence 1 means "this row is the whole company".
    evidence: dict[int, tuple[str, float]] = {}
    for link in resolved.links:
        for index in (link.left, link.right):
            current = evidence.get(index)
            if current is None or link.confidence > current[1]:
                evidence[index] = (link.method, link.confidence)

    ordered_roots = sorted(clusters, key=lambda root: min(reg.company_id for reg in clusters[root]))
    entities: list[dict] = []
    for number, root in enumerate(ordered_roots, start=1):
        members = clusters[root]
        entity_id = f"ENT-{number:05d}"
        canonical = _canonical_member(members)
        roles: list[str] = []
        for member in members:
            for role in member.roles:
                if role not in roles:
                    roles.append(role)
        entities.append({
            "entity_id": entity_id,
            "canonical_name": canonical.raw_name,
            "on_platform": True,
            "party_kind": "company",
            "roles": roles,
            "year_established": _best_year(members),
            "employee_range": _best_employee(members),
            "country_iso2": canonical.country_iso2,
            "city": canonical.city,
            "member_ids": [member.company_id for member in members],
            "cores": sorted({member.core for member in members if member.core}),
        })
        for member in members:
            resolved.entity_of[member.company_id] = entity_id
            method, confidence = evidence.get(member.index, ("singleton", 1.0))
            resolved.link_of[member.company_id] = (method, confidence)
    resolved.entities = entities


def _canonical_member(members: list[Registration]) -> Registration:
    """Richest registration, then the longer legal name, then the earliest id."""
    return max(
        members,
        key=lambda reg: (reg.richness, len(reg.raw_name), -_id_number(reg.company_id)),
    )


def _id_number(company_id: str) -> int:
    digits = "".join(ch for ch in company_id if ch.isdigit())
    return int(digits or 0)


def _best_year(members: list[Registration]) -> int | None:
    ranked = sorted(members, key=lambda reg: (reg.richness, -_id_number(reg.company_id)), reverse=True)
    for reg in ranked:
        if reg.year is not None:
            return reg.year
    return None


def _best_employee(members: list[Registration]) -> str | None:
    ranked = sorted(members, key=lambda reg: (reg.richness, -_id_number(reg.company_id)), reverse=True)
    for reg in ranked:
        if reg.employee_range:
            return reg.employee_range
    return None


def activity_class(roles: list[str], has_listings: bool) -> str:
    """Trading-versus-manufacturing flag from the ontology rule.

    Manufacturing is declared, or the company publishes listings and is not
    only a trader, importer, distributor, or wholesaler. A pure trader with
    listings stays a trader. Both signals produce ``mixed``.
    """
    role_set = set(roles)
    declares_mfg = "manufacturer" in role_set
    trader_signal = bool(role_set & _TRADER_ROLES)
    only_trader = bool(role_set) and role_set <= _TRADER_ROLES and not declares_mfg
    mfg_signal = declares_mfg or (has_listings and not only_trader)
    if mfg_signal and trader_signal:
        return "mixed"
    if mfg_signal:
        return "manufacturer"
    if trader_signal:
        return "trader"
    return "unknown"


def score_labels(resolved: Resolution, labels: pd.DataFrame) -> dict:
    by_id = {reg.company_id: reg for reg in resolved.registrations}
    tp = fp = fn = tn = 0
    false_pos = []
    false_neg = []
    for row in labels.itertuples(index=False):
        left = by_id[row.company_id_a]
        right = by_id[row.company_id_b]
        predicted = resolved.same(left.index, right.index)
        actual = int(row.is_same_entity) == 1
        if predicted and actual:
            tp += 1
        elif predicted and not actual:
            fp += 1
            false_pos.append(row.pair_id)
        elif not predicted and actual:
            fn += 1
            false_neg.append(row.pair_id)
        else:
            tn += 1
    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    sizes = defaultdict(int)
    for reg in resolved.registrations:
        sizes[resolved.find(reg.index)] += 1
    histogram = defaultdict(int)
    for size in sizes.values():
        histogram[size] += 1
    return {
        "pairs": int(len(labels)),
        "tp": tp,
        "fp": fp,
        "fn": fn,
        "tn": tn,
        "precision": precision,
        "recall": recall,
        "f1": f1,
        "entities": len(sizes),
        "registrations": len(resolved.registrations),
        "cluster_size_histogram": dict(sorted(histogram.items())),
        "false_positive_pairs": false_pos,
        "false_negative_pairs": false_neg,
    }
