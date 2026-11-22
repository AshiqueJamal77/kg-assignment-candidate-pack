"""Cleaning helpers shared by entity resolution, party linking, and graph load.

Source strings are not overwritten. These functions only produce the keys and
canonical values that relationships point at.
"""

from __future__ import annotations

import re
import unicodedata
from urllib.parse import urlparse

# Legal and generic suffixes. Distinctive words (trading, food, steel, ...) stay.
_SUFFIXES = {
    "pvt", "private", "ltd", "limited", "llc", "llp", "inc", "incorporated",
    "corp", "corporation", "co", "company", "gmbh", "kg", "ag", "sa", "sae",
    "srl", "sarl", "bv", "nv", "plc", "fze", "fzc", "fzco", "sdn", "bhd", "pte",
    "pt", "tbk", "spa", "sas", "ab", "oy", "as", "sti", "san", "tic", "ve",
    "und", "and", "the", "of", "mfg", "wll", "pjsc", "jsc", "ojsc", "est",
    "establishment", "proprietary", "sendirian", "berhad", "ltda", "imp", "exp",
    "impex", "ms", "messrs", "lp", "fz", "fze", "ltda", "lda", "plc", "ulc",
    "ooo", "zao", "ao", "kk", "gk", "yk", "bvba", "nvsa", "sarl", "eirl",
    "joint", "stock", "jsc", "opc", "huf",
}

_TOKEN_ALIAS = {
    "el": "al",
    "shree": "sri",
    "shri": "sri",
    "sree": "sri",
}

_FREE_EMAIL = {
    "gmail.com", "yahoo.com", "hotmail.com", "outlook.com", "live.com",
    "aol.com", "mail.com", "icloud.com", "ymail.com", "protonmail.com",
    "gmx.com", "yahoo.co.in", "yahoo.co.uk", "hotmail.co.uk",
}

_STREET = re.compile(
    r"\b(road|street|st|estate|park|district|zone|highway|area|centre|center|"
    r"bay|nagar|marg|lane|avenue|ave|plot|phase)\b",
    re.I,
)


def fold(text: str) -> str:
    """ASCII-fold a name so Öztürk and Ozturk share a key."""
    if text is None:
        return ""
    text = str(text).replace("İ", "I").replace("ı", "i")
    text = unicodedata.normalize("NFKD", text)
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    text = text.replace("ß", "ss").replace("æ", "ae").replace("ø", "o").replace("đ", "d").replace("ł", "l")
    return text


def _split_camel(text: str) -> str:
    text = re.sub(r"([a-z])([A-Z])", r"\1 \2", text)
    text = re.sub(r"([A-Z]+)([A-Z][a-z])", r"\1 \2", text)
    return text


def strip_embedded_address(name: str) -> str:
    """Drop a street address that was concatenated after the legal name.

    Shipment rows look like ``ACME LTD, 12, HARBOUR ROAD, PENANG``. The comma
    inside ``Co., Ltd.`` is kept, because that fragment is not a street number.
    """
    parts = [p.strip(" .") for p in str(name).split(",")]
    if not parts:
        return ""
    kept = [parts[0]]
    for part in parts[1:]:
        if not part:
            continue
        if re.match(r"^\d+\b", part):
            break
        if _STREET.search(part) and re.search(r"\d", part):
            break
        kept.append(part)
    return " ".join(kept)


def core_tokens(name: str, *, strip_address: bool = False) -> list[str]:
    text = strip_embedded_address(name) if strip_address else str(name or "")
    text = _split_camel(fold(text)).lower().replace("&", " and ")
    text = re.sub(r"[^a-z0-9\s]", " ", text)
    tokens: list[str] = []
    for token in text.split():
        if len(token) <= 1 or token in _SUFFIXES:
            continue
        # "alrawda" / "elhadaf", but not "electrical" or "aluminium".
        if token.startswith(("al", "el")) and len(token) > 4 and token[2] not in "aeiou":
            token = "al " + token[2:]
            tokens.extend(core_tokens(token))
            continue
        token = _TOKEN_ALIAS.get(token, token)
        if token and token not in _SUFFIXES and len(token) > 1:
            tokens.append(token)
    return tokens


def core_name(name: str, *, strip_address: bool = False) -> str:
    return " ".join(core_tokens(name, strip_address=strip_address))


def digits(value: str) -> str:
    return re.sub(r"\D", "", str(value or ""))


def phone_key(value: str, length: int = 8) -> str:
    """Last `length` digits. Empty when the number is too short to be stable."""
    number = digits(value)
    if len(number) < length:
        return ""
    return number[-length:]


def website_host(value: str) -> str:
    raw = str(value or "").strip().lower()
    if not raw or raw in {"nan", "none", "-"}:
        return ""
    if "://" not in raw:
        raw = "http://" + raw
    host = urlparse(raw).netloc.lower().split("@")[-1]
    if host.startswith("www."):
        host = host[4:]
    return host.split(":")[0]


def email_address(value: str) -> str:
    raw = str(value or "").strip().lower()
    if "@" not in raw:
        return ""
    return raw


def email_domain(value: str) -> str:
    address = email_address(value)
    if not address:
        return ""
    return address.split("@", 1)[1]


def corporate_email_domain(value: str) -> str:
    domain = email_domain(value)
    if domain in _FREE_EMAIL:
        return ""
    return domain


def address_key(address: str) -> str:
    text = fold(str(address or "")).lower()
    text = re.sub(r"[^a-z0-9]", "", text)
    if len(text) < 4:
        return ""
    return text


def parse_year(value) -> int | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text or text.lower() in {"nan", "none"}:
        return None
    try:
        year = int(float(text))
    except ValueError:
        return None
    if year < 1800 or year > 2030:
        return None
    return year


def years_compatible(left: int | None, right: int | None, slack: int = 1) -> bool:
    if left is None or right is None:
        return True
    return abs(left - right) <= slack


def parse_number(value) -> float | None:
    if value is None:
        return None
    text = str(value).strip().replace(",", "")
    if not text or text.lower() in {"nan", "none"}:
        return None
    try:
        number = float(text)
    except ValueError:
        return None
    return number


def blank_to_none(value) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text or text.lower() in {"nan", "none"}:
        return None
    return text
