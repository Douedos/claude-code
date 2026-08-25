#!/usr/bin/env python3
"""Staging: deterministic transforms from raw/ to a canonical country panel.

Output: panel/country_panel.csv with unique ISO3 keys, AI diffusion for
H1 2025, H2 2025, Q1 2026, GDP per capita (2023, current US$), population,
and M49 region tags. All drops are reported explicitly.
"""
import csv, json, os, re, sys

BASE = os.path.dirname(os.path.abspath(__file__))

def read_csv(path, encoding="utf-8-sig"):
    with open(path, newline="", encoding=encoding) as f:
        return list(csv.DictReader(f))

# --- Microsoft adoption ---
# Microsoft CSV ships in Mac-Roman encoding (verified: 0x9f decodes to the
# u-umlaut in Turkiye under mac_roman; the byte is invalid UTF-8)
ms = read_csv(os.path.join(BASE, "raw/S02_AI_Diffusion_Q12026_Update.csv"),
              encoding="mac_roman")
def pct(x):
    x = x.strip()
    if not x or x in ("-", "n/a", "NA"): return None
    return float(x.rstrip("%"))
adoption = {}
for r in ms:
    name = r["Economy"].strip()
    adoption[name] = dict(h1_2025=pct(r["H1 2025 AI Diffusion"]),
                          h2_2025=pct(r["H2 2025 AI Diffusion"]),
                          q1_2026=pct(r["Q1 2026 AI Diffusion"]))
assert len(adoption) == len(ms), "duplicate economy names in Microsoft CSV"

# --- Concordance: name -> ISO3 ---
cc = read_csv(os.path.join(BASE, "raw/X02_country_codes.csv"))
name_to_iso, iso_meta = {}, {}
for r in cc:
    iso3 = r.get("ISO3166-1-Alpha-3", "").strip()
    if not iso3: continue
    iso_meta[iso3] = dict(region=r.get("Region Name", ""), subregion=r.get("Sub-region Name", ""),
                          ldc=bool(r.get("Least Developed Countries (LDC)", "").strip()))
    for col in ("official_name_en", "UNTERM English Short", "CLDR display name"):
        n = r.get(col, "").strip()
        if n: name_to_iso.setdefault(n.lower(), iso3)

MANUAL = {  # Microsoft economy names not matched by the concordance name columns
    "south korea": "KOR", "taiwan": "TWN", "hong kong sar": "HKG", "hong kong": "HKG",
    "macao sar": "MAC", "vietnam": "VNM", "russia": "RUS", "iran": "IRN",
    "turkiye": "TUR", "türkiye": "TUR", "syria": "SYR", "laos": "LAO",
    "moldova": "MDA", "tanzania": "TZA", "bolivia": "BOL", "venezuela": "VEN",
    "brunei": "BRN", "czech republic": "CZE", "czechia": "CZE", "ivory coast": "CIV",
    "cote d'ivoire": "CIV", "côte d'ivoire": "CIV", "democratic republic of the congo": "COD",
    "congo (drc)": "COD",
    "republic of the congo": "COG", "congo": "COG", "cape verde": "CPV",
    "united states": "USA", "united kingdom": "GBR", "netherlands": "NLD",
    "north macedonia": "MKD", "kosovo": "XKX", "palestine": "PSE",
    "west bank and gaza": "PSE", "swaziland": "SWZ", "eswatini": "SWZ",
    "myanmar": "MMR", "the gambia": "GMB", "gambia": "GMB", "bahamas": "BHS",
    "saint lucia": "LCA", "trinidad and tobago": "TTO", "puerto rico": "PRI",
    "dominican republic": "DOM", "el salvador": "SLV", "sri lanka": "LKA",
    "north korea": "PRK", "south sudan": "SSD", "sudan": "SDN",
    "guinea-bissau": "GNB", "equatorial guinea": "GNQ", "papua new guinea": "PNG",
    "new caledonia": "NCL", "french polynesia": "PYF", "timor-leste": "TLS",
    "east timor": "TLS", "curacao": "CUW", "curaçao": "CUW", "aruba": "ABW",
    "sint maarten": "SXM", "cayman islands": "CYM", "bermuda": "BMU",
    "isle of man": "IMN", "jersey": "JEY", "guernsey": "GGY", "gibraltar": "GIB",
    "faroe islands": "FRO", "greenland": "GRL", "reunion": "REU", "réunion": "REU",
    "guadeloupe": "GLP", "martinique": "MTQ", "french guiana": "GUF", "mayotte": "MYT",
}

unmatched, rows = [], {}
for name, vals in adoption.items():
    iso = name_to_iso.get(name.lower()) or MANUAL.get(name.lower())
    if not iso:
        unmatched.append(name); continue
    if iso in rows:
        print(f"DUPLICATE ISO {iso} from {name}"); sys.exit(1)
    rows[iso] = dict(iso3=iso, economy=name, **vals)

# --- World Bank GDP + population (mirror vintages) ---
def wb_latest(path, min_year=2019):
    data = {}
    for r in read_csv(path):
        code, yr, v = r["Country Code"].strip(), int(r["Year"]), r["Value"].strip()
        if not v or yr < min_year: continue
        cur = data.get(code)
        if cur is None or yr > cur[0]: data[code] = (yr, float(v))
    return data

gdp = wb_latest(os.path.join(BASE, "raw/S15_wb_gdp_current_usd.csv"))
pop = wb_latest(os.path.join(BASE, "raw/X01_wb_population.csv"))

for iso, r in rows.items():
    g, p = gdp.get(iso), pop.get(iso)
    r["gdp_usd"] = g[1] if g else None
    r["gdp_year"] = g[0] if g else None
    r["pop"] = p[1] if p else None
    r["pop_year"] = p[0] if p else None
    r["gdp_pc"] = (g[1] / p[1]) if (g and p) else None
    meta = iso_meta.get(iso, {})
    r["region"] = meta.get("region", "")
    r["subregion"] = meta.get("subregion", "")
    r["ldc"] = meta.get("ldc", False)

os.makedirs(os.path.join(BASE, "panel"), exist_ok=True)
fields = ["iso3","economy","h1_2025","h2_2025","q1_2026","gdp_usd","gdp_year",
          "pop","pop_year","gdp_pc","region","subregion","ldc"]
with open(os.path.join(BASE, "panel/country_panel.csv"), "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=fields)
    w.writeheader()
    for iso in sorted(rows): w.writerow({k: rows[iso][k] for k in fields})

report = dict(
    microsoft_economies=len(adoption),
    matched=len(rows),
    unmatched_economies=unmatched,
    missing_gdp=[i for i, r in rows.items() if r["gdp_pc"] is None],
    gdp_vintage_years=sorted({r["gdp_year"] for r in rows.values() if r["gdp_year"]}),
    pop_vintage_years=sorted({r["pop_year"] for r in rows.values() if r["pop_year"]}),
)
json.dump(report, open(os.path.join(BASE, "panel/staging_report.json"), "w"), indent=2)
print(json.dumps(report, indent=2))
