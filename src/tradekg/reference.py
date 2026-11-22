"""Closed vocabularies: countries, cities, ports, units, certificates.

Aliases are the spellings that actually occur in the files, plus the old/new
city names the ontology calls out. A string that is not in these maps stays on
the source node as a raw property and does not grow a guessed relationship.
"""

from __future__ import annotations

import re

from tradekg.normalize import fold

# iso2, iso3, canonical English name, aliases (folded lower).
_COUNTRIES = [
    ("AE", "ARE", "United Arab Emirates", [
        "united arab emirates", "u.a.e.", "uae", "emirates",
    ]),
    ("IN", "IND", "India", [
        "india", "republic of india", "ind",
    ]),
    ("US", "USA", "United States", [
        "united states", "united states of america", "u.s.a.", "usa", "us",
    ]),
    ("CN", "CHN", "China", [
        "china", "people's republic of china", "peoples republic of china",
        "chn", "prc",
    ]),
    ("SA", "SAU", "Saudi Arabia", [
        "saudi arabia", "kingdom of saudi arabia", "ksa", "k.s.a.",
    ]),
    ("GB", "GBR", "United Kingdom", [
        "united kingdom", "uk", "u.k.", "great britain", "england",
    ]),
    ("VN", "VNM", "Vietnam", [
        "vietnam", "viet nam", "socialist republic of vietnam",
    ]),
    ("MY", "MYS", "Malaysia", [
        "malaysia", "federation of malaysia", "mys",
    ]),
    ("DE", "DEU", "Germany", [
        "germany", "deutschland", "federal republic of germany", "deu",
    ]),
    ("KE", "KEN", "Kenya", [
        "kenya", "republic of kenya", "ken",
    ]),
    ("TR", "TUR", "Turkey", [
        "turkey", "turkiye", "türkiye", "tur",
    ]),
    ("ZA", "ZAF", "South Africa", [
        "south africa", "republic of south africa", "s. africa", "rsa",
    ]),
    ("EG", "EGY", "Egypt", [
        "egypt", "arab republic of egypt", "egy",
    ]),
    ("IT", "ITA", "Italy", [
        "italy", "italia", "ita",
    ]),
    ("BD", "BGD", "Bangladesh", [
        "bangladesh", "people's republic of bangladesh",
        "peoples republic of bangladesh", "bgd",
    ]),
    ("ID", "IDN", "Indonesia", [
        "indonesia", "republic of indonesia", "idn",
    ]),
    ("LK", "LKA", "Sri Lanka", [
        "sri lanka", "democratic socialist republic of sri lanka", "ceylon", "lka",
    ]),
    ("PK", "PAK", "Pakistan", [
        "pakistan", "islamic republic of pakistan", "pak",
    ]),
    ("BR", "BRA", "Brazil", [
        "brazil", "brasil", "bra",
    ]),
]

_COUNTRY_BY_ALIAS: dict[str, tuple[str, str, str]] = {}
for _iso2, _iso3, _name, _aliases in _COUNTRIES:
    for alias in _aliases + [_name.lower(), _iso2.lower(), _iso3.lower()]:
        _COUNTRY_BY_ALIAS[fold(alias).lower()] = (_iso2, _iso3, _name)


def country_record(raw: str) -> tuple[str, str, str] | None:
    key = fold(str(raw or "")).lower().strip()
    key = re.sub(r"\s+", " ", key).strip(".")
    found = _COUNTRY_BY_ALIAS.get(key)
    if found:
        return found
    # "U.A.E." and "U.S.A." lose their dots and land on the UAE / USA aliases.
    return _COUNTRY_BY_ALIAS.get(key.replace(".", ""))


def all_countries() -> list[dict]:
    rows = []
    for iso2, iso3, name, aliases in _COUNTRIES:
        observed = sorted({name, *aliases})
        rows.append({"iso2": iso2, "iso3": iso3, "name": name, "aliases": observed})
    return rows


# Old name -> canonical city. Keys are folded lower-case.
_CITY_ALIAS = {
    "amdavad": "ahmedabad",
    "ahmedabad": "ahmedabad",
    "antep": "gaziantep",
    "gaziantep": "gaziantep",
    "bombay": "mumbai",
    "mumbai": "mumbai",
    "calcutta": "kolkata",
    "kolkata": "kolkata",
    "canton": "guangzhou",
    "guangzhou": "guangzhou",
    "chittagong": "chattogram",
    "chattogram": "chattogram",
    "cochin": "kochi",
    "kochi": "kochi",
    "cologne": "cologne",
    "koeln": "cologne",
    "koln": "cologne",
    "dacca": "dhaka",
    "dhaka": "dhaka",
    "delhi": "delhi",
    "new delhi": "delhi",
    "duesseldorf": "dusseldorf",
    "dusseldorf": "dusseldorf",
    "frankfurt am main": "frankfurt",
    "frankfurt": "frankfurt",
    "gurgaon": "gurugram",
    "gurugram": "gurugram",
    "hcmc": "ho chi minh city",
    "saigon": "ho chi minh city",
    "ho chi minh city": "ho chi minh city",
    "ho chi minh": "ho chi minh city",
    "ha noi": "hanoi",
    "hanoi": "hanoi",
    "hai phong": "haiphong",
    "haiphong": "haiphong",
    "jb": "johor bahru",
    "johor bahru": "johor bahru",
    "jiddah": "jeddah",
    "jeddah": "jeddah",
    "joburg": "johannesburg",
    "johannesburg": "johannesburg",
    "al jubail": "jubail",
    "jubail": "jubail",
    "kl": "kuala lumpur",
    "kuala lumpur": "kuala lumpur",
    "la": "los angeles",
    "los angeles": "los angeles",
    "madras": "chennai",
    "chennai": "chennai",
    "milan": "milan",
    "milano": "milan",
    "naples": "naples",
    "napoli": "naples",
    "genoa": "genoa",
    "genova": "genoa",
    "munich": "munich",
    "muenchen": "munich",
    "munchen": "munich",
    "nyc": "new york",
    "new york": "new york",
    "rio": "rio de janeiro",
    "rio de janeiro": "rio de janeiro",
    "sao paulo": "sao paulo",
    "10th of ramadan city": "10th of ramadan",
    "tenth of ramadan": "10th of ramadan",
    "tirupur": "tiruppur",
    "tiruppur": "tiruppur",
    "vitoria": "vitoria",
    "istanbul": "istanbul",
    "izmir": "izmir",
    "penang": "penang",
    "pulau pinang": "penang",
}


def canonical_city(raw: str) -> str:
    text = fold(str(raw or "")).lower().strip()
    text = re.sub(r"\s+", " ", text)
    if not text:
        return ""
    return _CITY_ALIAS.get(text, text)


# port_id, canonical name, unlocode or "", country iso2, raw aliases.
_PORTS = [
    ("AEJEA", "Jebel Ali", "AEJEA", "AE", ["AEJEA", "Jebel Ali", "Jebel Ali Port", "Dubai (Jebel Ali)"]),
    ("AEKHL", "Khalifa Port", "AEKHL", "AE", ["Khalifa Port", "Abu Dhabi Khalifa Port"]),
    ("AESHJ", "Port Khalid", "AESHJ", "AE", ["Khalid Port", "Port Khalid", "Sharjah Port"]),
    ("EGALY", "Alexandria", "EGALY", "EG", ["Alexandria", "Alexandria Port", "EGALY"]),
    ("EGSOK", "Ain Sokhna", "EGSOK", "EG", ["Ain Sokhna", "Sokhna"]),
    ("EGPSD", "Port Said", "EGPSD", "EG", ["Port Said"]),
    ("EGPSC", "East Port Said", "EGPSC", "EG", ["East Port Said"]),
    ("EGEDK", "El Dekheila", "EGEDK", "EG", ["El Dekheila"]),
    ("TRALI", "Izmir Alsancak", "TRALI", "TR", ["Alsancak", "Izmir"]),
    ("TRAMR", "Ambarli", "TRAMR", "TR", ["Ambarli", "Istanbul (Ambarli)"]),
    ("TRMER", "Mersin", "TRMER", "TR", ["Mersin", "Mersin Port", "TRMER"]),
    ("TRGEM", "Gemlik", "TRGEM", "TR", ["Gemlik"]),
    ("BDCGP", "Chattogram", "BDCGP", "BD", ["BDCGP", "Chattogram", "Chittagong", "Chittagong Port"]),
    ("BDMGL", "Mongla", "BDMGL", "BD", ["Mongla", "Mongla Port"]),
    ("BRSSZ", "Santos", "BRSSZ", "BR", ["BRSSZ", "Santos", "Porto de Santos"]),
    ("BRPNG", "Paranagua", "BRPNG", "BR", ["Paranagua", "Paranaguá"]),
    ("BRVIX", "Vitoria", "BRVIX", "BR", ["Vitoria", "Vitória"]),
    ("BRRIO", "Rio de Janeiro", "BRRIO", "BR", ["Rio Port", "Rio de Janeiro"]),
    ("IDBLW", "Belawan", "IDBLW", "ID", ["Belawan", "Medan Belawan"]),
    ("IDDUM", "Dumai", "IDDUM", "ID", ["Dumai"]),
    ("IDSUB", "Tanjung Perak", "IDSUB", "ID", ["Surabaya", "Tanjung Perak"]),
    ("IDJKT", "Tanjung Priok", "IDJKT", "ID", ["Jakarta", "Tanjung Priok", "Tg. Priok"]),
    ("PKBQM", "Port Qasim", "PKBQM", "PK", ["Bin Qasim", "Port Qasim"]),
    ("PKKHI", "Karachi", "PKKHI", "PK", ["Karachi", "Karachi Port", "PKKHI"]),
    ("DEBRV", "Bremerhaven", "DEBRV", "DE", ["Bremerhaven", "Bremerhaven Port"]),
    ("DEHAM", "Hamburg", "DEHAM", "DE", ["Hamburg", "Port of Hamburg", "DEHAM"]),
    ("CNNGB", "Ningbo", "CNNGB", "CN", ["CNNGB", "Ningbo", "Ningbo-Zhoushan"]),
    ("CNSHA", "Shanghai", "CNSHA", "CN", ["CNSHA", "Shanghai", "Shanghai Port"]),
    ("CNTAO", "Qingdao", "CNTAO", "CN", ["Qingdao", "Qingdao Port"]),
    ("CNXMN", "Xiamen", "CNXMN", "CN", ["Xiamen", "Xiamen Port"]),
    ("CNTXG", "Tianjin Xingang", "CNTXG", "CN", ["Tianjin", "Tianjin Xingang", "Xingang"]),
    ("CNYTN", "Yantian", "CNYTN", "CN", ["Yantian"]),
    ("CNSHK", "Shekou", "CNSHK", "CN", ["Shekou", "Shenzhen"]),
    ("VNCMT", "Cai Mep", "VNCMT", "VN", ["Cai Mep"]),
    ("VNSGN", "Ho Chi Minh City", "VNSGN", "VN", ["Cat Lai", "Ho Chi Minh", "Saigon Port", "VNSGN"]),
    ("VNHPH", "Haiphong", "VNHPH", "VN", ["Hai Phong Port", "Haiphong"]),
    ("VNDAD", "Da Nang", "VNDAD", "VN", ["Da Nang Port"]),
    ("ZACPT", "Cape Town", "ZACPT", "ZA", ["Cape Town", "Cape Town Port"]),
    ("ZADUR", "Durban", "ZADUR", "ZA", ["Durban", "Port of Durban", "ZADUR"]),
    ("ZAPLZ", "Gqeberha", "ZAPLZ", "ZA", ["Gqeberha", "Port Elizabeth"]),
    ("INCCU", "Kolkata", "INCCU", "IN", ["Calcutta Port", "Kolkata", "Kolkata Port"]),
    ("INMAA", "Chennai", "INMAA", "IN", ["Chennai", "Chennai Port", "Madras Port", "INMAA"]),
    ("INCOK", "Cochin", "INCOK", "IN", ["Cochin", "Cochin Port", "Kochi Port"]),
    ("INMUN", "Mundra", "INMUN", "IN", ["Mundra", "Mundra Port", "INMUN"]),
    ("INNSA", "Nhava Sheva", "INNSA", "IN", ["INNSA", "JNPT", "Jawaharlal Nehru Port", "Nhava Sheva"]),
    ("LKCMB", "Colombo", "LKCMB", "LK", ["Colombo", "Colombo Port", "LKCMB"]),
    ("LKHBA", "Hambantota", "LKHBA", "LK", ["Hambantota", "Hambantota Port"]),
    ("GBFXT", "Felixstowe", "GBFXT", "GB", ["Felixstowe", "GBFXT"]),
    ("GBLGW", "London Gateway", "GBLGW", "GB", ["London Gateway"]),
    ("GBLIV", "Liverpool", "GBLIV", "GB", ["Liverpool"]),
    ("GBSOU", "Southampton", "GBSOU", "GB", ["Southampton", "Port of Southampton"]),
    ("ITGOA", "Genoa", "ITGOA", "IT", ["Genoa", "Genova", "ITGOA"]),
    ("ITSPE", "La Spezia", "ITSPE", "IT", ["La Spezia"]),
    ("ITLIV", "Livorno", "ITLIV", "IT", ["Livorno"]),
    ("ITNAP", "Naples", "ITNAP", "IT", ["Naples", "Napoli"]),
    ("KEMBA", "Mombasa", "KEMBA", "KE", ["KEMBA", "Kilindini", "Mombasa", "Mombasa Port"]),
    ("SAJED", "Jeddah", "SAJED", "SA", ["SAJED", "Jeddah", "Jeddah Islamic Port"]),
    ("SAJUB", "Jubail", "SAJUB", "SA", ["Jubail", "Jubail Port"]),
    ("SADMM", "Dammam", "SADMM", "SA", ["Dammam", "Dammam Port", "King Abdulaziz Port"]),
    ("MYPKG", "Port Klang", "MYPKG", "MY", ["Klang", "Port Klang", "MYPKG"]),
    ("MYPEN", "Penang", "MYPEN", "MY", ["Penang", "Penang Port"]),
    ("MYTPP", "Tanjung Pelepas", "MYTPP", "MY", ["PTP", "Tanjung Pelepas"]),
    ("MYPGU", "Pasir Gudang", "MYPGU", "MY", ["Pasir Gudang"]),
    ("USLAX", "Los Angeles", "USLAX", "US", ["Los Angeles", "USLAX"]),
    ("USLGB", "Long Beach", "USLGB", "US", ["Long Beach"]),
    ("USLAX-LGB", "Los Angeles / Long Beach", "", "US", ["LA/Long Beach"]),
    ("USNYC", "New York / Newark", "USNYC", "US", ["NY/NJ", "New York", "Newark", "USNYC"]),
    ("USHOU", "Houston", "USHOU", "US", ["Houston", "Port of Houston"]),
    ("USSAV", "Savannah", "USSAV", "US", ["Savannah", "Port of Savannah"]),
]

_PORT_BY_ALIAS: dict[str, dict] = {}
for _pid, _name, _locode, _iso, _aliases in _PORTS:
    record = {
        "port_id": _pid,
        "name": _name,
        "unlocode": _locode or None,
        "country_iso2": _iso,
        "aliases": list(_aliases),
    }
    for alias in _aliases:
        _PORT_BY_ALIAS[alias.strip().lower()] = record


def port_record(raw: str) -> dict | None:
    return _PORT_BY_ALIAS.get(str(raw or "").strip().lower())


def all_ports() -> list[dict]:
    return [
        {
            "port_id": pid,
            "name": name,
            "unlocode": locode or None,
            "country_iso2": iso,
            "aliases": list(aliases),
        }
        for pid, name, locode, iso, aliases in _PORTS
    ]


_UNITS = [
    ("KG", "mass", ["KG", "KGS", "KGM", "KILOGRAM", "KILOGRAMS", "KILO"]),
    ("MT", "mass", ["MT", "MTS", "TON", "TONS", "TNE", "M/T", "MTON"]),
    ("G", "mass", ["G", "GRM", "GMS", "GRAM", "GRAMS"]),
    ("PCS", "count", ["PCS", "PIECE", "PIECES", "PCE", "NOS", "UNITS", "UNIT", "PC"]),
    ("SQM", "area", ["SQM", "M2", "SQ MTR", "SQMTR", "SQ.M"]),
    ("CT", "mass", ["CT", "CTS", "CARAT", "CARATS"]),
    ("PAIRS", "count", ["PAIRS", "PRS", "PR", "PAIR"]),
]

_UNIT_BY_ALIAS = {}
for _code, _dim, _aliases in _UNITS:
    for alias in _aliases:
        _UNIT_BY_ALIAS[alias.strip().lower()] = _code


def canonical_unit(raw: str) -> str | None:
    key = fold(str(raw or "")).lower().strip().rstrip(".")
    key = re.sub(r"\s+", " ", key)
    return _UNIT_BY_ALIAS.get(key)


def all_units() -> list[dict]:
    return [
        {"code": code, "dimension": dim, "aliases": list(aliases)}
        for code, dim, aliases in _UNITS
    ]


# code, display name, family, alias substrings matched against a normalized blob.
_CERTS = [
    ("ISO_9001", "ISO 9001", "quality", [r"iso\s*-?\s*9001"]),
    ("ISO_14001", "ISO 14001", "quality", [r"iso\s*-?\s*14001"]),
    ("ISO_22000", "ISO 22000", "food_safety", [r"iso\s*-?\s*22000"]),
    ("IATF_16949", "IATF 16949", "automotive", [r"iatf\s*-?\s*16949", r"ts\s*-?\s*16949", r"\biatf\b"]),
    ("CE", "CE", "regulatory", [r"\bce\b"]),
    ("BIS", "BIS", "regulatory", [r"\bbis\b"]),
    ("UL", "UL", "regulatory", [r"\bul\b"]),
    ("FDA", "US FDA", "regulatory", [r"\bus\s*-?\s*fda\b", r"\bfda\b", r"\busfda\b"]),
    ("HALAL", "Halal", "food_safety", [r"\bhalal\b"]),
    ("FSSC_22000", "FSSC 22000", "food_safety", [r"fssc\s*-?\s*22000"]),
    ("HACCP", "HACCP", "food_safety", [r"\bhaccp\b"]),
    ("BRCGS", "BRCGS", "food_safety", [r"\bbrcgs\b", r"\bbrc\b"]),
    ("KOSHER", "Kosher", "food_safety", [r"\bkosher\b"]),
    ("USDA_ORGANIC", "USDA Organic", "organic", [r"usda\s*organic"]),
    ("GOTS", "GOTS", "organic", [r"\bgots\b"]),
    ("GMP", "GMP", "quality", [r"\bgmp\b"]),
    ("API_5L", "API 5L", "regulatory", [r"api\s*-?\s*5l"]),
    ("EN71", "EN 71", "regulatory", [r"\ben\s*-?\s*71\b"]),
    ("ECE_R90", "ECE R90", "automotive", [r"ece\s*-?\s*r\s*-?\s*90"]),
    ("DOT", "DOT", "automotive", [r"\bdot\b"]),
    ("E_MARK", "E-Mark", "automotive", [r"e\s*-?\s*mark"]),
    ("RJC", "RJC", "other", [r"\brjc\b"]),
    ("FSC", "FSC", "other", [r"\bfsc\b"]),
    ("BSCI", "BSCI", "social", [r"\bbsci\b"]),
    ("SEDEX", "SEDEX", "social", [r"\bsedex\b"]),
    ("WRAP", "WRAP", "social", [r"\bwrap\b"]),
    ("REACH", "REACH", "regulatory", [r"\breach\b"]),
    ("ROHS", "RoHS", "regulatory", [r"\brohs\b"]),
    ("OEKO_TEX", "OEKO-TEX Standard 100", "other", [r"oeko\s*-?\s*tex", r"oekotex"]),
    ("LWG", "LWG", "other", [r"\blwg\b"]),
    ("KIMBERLEY", "Kimberley Process", "other", [r"kimberley", r"\bkpcs\b", r"kp\s*compliant"]),
]

_CERT_PATTERNS = [
    (code, name, family, [re.compile(pat, re.I) for pat in pats])
    for code, name, family, pats in _CERTS
]


def parse_certifications(raw: str) -> list[tuple[str, str]]:
    """Return (code, matched raw fragment) pairs, one per canonical certificate."""
    text = str(raw or "").strip()
    if not text or text.lower() in {"nan", "none"}:
        return []
    found: list[tuple[str, str]] = []
    seen = set()
    for code, _name, _family, patterns in _CERT_PATTERNS:
        for pattern in patterns:
            match = pattern.search(text)
            if match and code not in seen:
                seen.add(code)
                found.append((code, match.group(0)))
                break
    return found


def all_certifications() -> list[dict]:
    return [
        {"code": code, "name": name, "family": family, "aliases": patterns}
        for code, name, family, patterns in _CERTS
    ]
