#!/usr/bin/env python3
"""Ingestion layer: fetch raw sources, store immutably, write manifests.

Egress note (2026-08-25 session): the sandbox network policy allows
github.com/raw.githubusercontent.com, microsoft.com and package registries only.
Registry hosts huggingface.co, openai.com, anthropic.com, openrouter.ai,
ec.europa.eu, imf.org, ilo.org/ilostat.ilo.org, worldbank.org/api.worldbank.org
are BLOCKED (proxy 403, policy denial). Sources on blocked hosts are recorded
in the manifest with status "blocked_by_egress" and are NOT silently replaced.
"""
import hashlib, json, os, subprocess, sys, datetime, urllib.request

BASE = os.path.dirname(os.path.abspath(__file__))
RAW = os.path.join(BASE, "raw")
MAN = os.path.join(BASE, "manifest")
UTC = datetime.datetime.now(datetime.timezone.utc).isoformat()

SOURCES = [
    # --- retrievable ---
    dict(id="S02", name="Microsoft AI Diffusion public repository (country CSV)",
         url="https://raw.githubusercontent.com/microsoft/ai-diffusion-report/main/data/AI_Diffusion_Q12026_Update.csv",
         local="S02_AI_Diffusion_Q12026_Update.csv", cls="CORE",
         license="see repo LICENSE.md (Microsoft)",
         fingerprint_expect="Economy,H1 2025 AI Diffusion,H2 2025 AI Diffusion,Q1 2026 AI Diffusion",
         channel="github raw (first-party Microsoft repo)"),
    dict(id="S02b", name="Microsoft AI Diffusion repo README (registry fingerprint check)",
         url="https://raw.githubusercontent.com/microsoft/ai-diffusion-report/main/README.md",
         local="S02b_README.md", cls="CORE",
         license="see repo LICENSE.md (Microsoft)",
         fingerprint_expect="This repository contains the datasets and report materials",
         channel="github raw (first-party Microsoft repo)"),
    dict(id="S01", name="Microsoft Global AI Diffusion Q1 2026 report PDF",
         url="https://raw.githubusercontent.com/microsoft/ai-diffusion-report/main/reports/Microsoft-AI-Diffusion-Report-2026-Q1.pdf",
         local="S01_Microsoft-AI-Diffusion-Report-2026-Q1.pdf", cls="CORE",
         license="see repo LICENSE.md (Microsoft)",
         fingerprint_expect=None, binary=True,
         channel="github raw (first-party Microsoft repo; registry URL on microsoft.com also reachable)"),
    dict(id="S01b", name="Microsoft Global AI Diffusion 2025 H1 report PDF (first release)",
         url="https://raw.githubusercontent.com/microsoft/ai-diffusion-report/main/reports/Microsoft-AI-Diffusion-Report-2025-H1.pdf",
         local="S01b_Microsoft-AI-Diffusion-Report-2025-H1.pdf", cls="CORE",
         license="see repo LICENSE.md (Microsoft)", fingerprint_expect=None, binary=True,
         channel="github raw (first-party Microsoft repo)"),
    dict(id="S15", name="World Bank GDP current US$ (Frictionless datasets/gdp mirror)",
         url="https://raw.githubusercontent.com/datasets/gdp/main/data/gdp.csv",
         local="S15_wb_gdp_current_usd.csv", cls="SUPPORTING",
         license="ODC-PDDL (mirror); underlying WB CC-BY 4.0",
         fingerprint_expect="Country Name,Country Code,Year,Value",
         channel="github raw (Frictionless Data mirror of World Bank API; first-party api.worldbank.org blocked)"),
    dict(id="X01", name="World Bank population total (Frictionless datasets/population mirror)",
         url="https://raw.githubusercontent.com/datasets/population/main/data/population.csv",
         local="X01_wb_population.csv", cls="SUPPORTING",
         license="ODC-PDDL (mirror); underlying WB CC-BY 4.0",
         fingerprint_expect="Country Name,Country Code,Year,Value",
         channel="github raw (Frictionless Data mirror; first-party api.worldbank.org blocked)"),
    dict(id="X02", name="Country codes / regions concordance (Frictionless datasets/country-codes)",
         url="https://raw.githubusercontent.com/datasets/country-codes/main/data/country-codes.csv",
         local="X02_country_codes.csv", cls="CONCORDANCE",
         license="ODC-PDDL",
         fingerprint_expect="ISO3166-1-Alpha-3",
         channel="github raw"),
    # --- blocked by egress policy: recorded, not fetched ---
    dict(id="S03", name="Anthropic Economic Index June 2026 data documentation",
         url="https://huggingface.co/datasets/Anthropic/EconomicIndex/blob/main/release_2026_06_26/data_documentation.md",
         local=None, cls="CORE", blocked="huggingface.co blocked by egress policy"),
    dict(id="S04", name="Anthropic Economic Index Sept 2025 geography report",
         url="https://www.anthropic.com/research/anthropic-economic-index-september-2025-report",
         local=None, cls="CORE", blocked="anthropic.com blocked by egress policy"),
    dict(id="S05", name="OpenAI Signals individual data",
         url="https://openai.com/signals/data/", local=None, cls="CORE",
         blocked="openai.com blocked by egress policy"),
    dict(id="S07", name="OpenRouter State of AI 2025",
         url="https://openrouter.ai/state-of-ai", local=None, cls="ROBUSTNESS",
         blocked="openrouter.ai blocked by egress policy"),
    dict(id="S08", name="Eurostat productivity trends (nama_10_lp_a21)",
         url="https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data/nama_10_lp_a21",
         local=None, cls="CORE OUTCOME", blocked="ec.europa.eu blocked by egress policy"),
    dict(id="S10", name="Eurostat services production (sts_sepr_m)",
         url="https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data/sts_sepr_m",
         local=None, cls="CORE OUTCOME", blocked="ec.europa.eu blocked by egress policy"),
    dict(id="S11", name="IMF WEO April 2026", url="https://www.imf.org/external/datamapper/datasets/WEO",
         local=None, cls="CORE MACRO", blocked="imf.org blocked by egress policy"),
    dict(id="S12", name="IMF WEO Database October 2024 (forecast baseline)",
         url="https://www.imf.org/en/publications/weo/weo-database/2024/october",
         local=None, cls="CORE MACRO", blocked="imf.org blocked by egress policy"),
    dict(id="S13", name="ILO ISCO-08 Vol I", url="https://webapps.ilo.org/ilostat-files/ISCO/newdocs-08-2021/ISCO-08/ISCO-08%20EN%20Vol%201.pdf",
         local=None, cls="CORE DENOMINATOR", blocked="webapps.ilo.org blocked by egress policy"),
    dict(id="S14", name="ILOSTAT employment by occupation", url="https://ilostat.ilo.org/data/",
         local=None, cls="CORE DENOMINATOR", blocked="ilostat.ilo.org blocked by egress policy"),
]

def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()

def main():
    os.makedirs(RAW, exist_ok=True); os.makedirs(MAN, exist_ok=True)
    manifest = []
    for s in SOURCES:
        rec = dict(source_id=s["id"], name=s["name"], url=s["url"],
                   use_class=s["cls"], retrieved_utc=UTC)
        if s.get("blocked"):
            rec.update(status="blocked_by_egress", detail=s["blocked"])
            manifest.append(rec); continue
        dest = os.path.join(RAW, s["local"])
        if not os.path.exists(dest):
            subprocess.run(["curl", "-sS", "-m", "120", "-o", dest, s["url"]], check=True)
        rec.update(status="retrieved", local_file=os.path.relpath(dest, BASE),
                   bytes=os.path.getsize(dest), sha256=sha256(dest),
                   license=s.get("license"), channel=s.get("channel"))
        fp = s.get("fingerprint_expect")
        if fp:
            head = open(dest, "r", errors="replace").read(4000)
            rec["fingerprint_expected"] = fp
            rec["fingerprint_match"] = fp in head
            if not rec["fingerprint_match"]:
                rec["status"] = "FINGERPRINT_MISMATCH_BLOCKED"
        manifest.append(rec)
    # repo-level vintage for the Microsoft clone
    try:
        head = subprocess.run(["git", "-C", "/home/user/microsoft/ai-diffusion-report",
                               "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip()
        manifest.append(dict(source_id="S02-vintage", name="microsoft/ai-diffusion-report git HEAD",
                             url="https://github.com/microsoft/ai-diffusion-report",
                             status="recorded", git_head=head, retrieved_utc=UTC))
    except Exception as e:
        manifest.append(dict(source_id="S02-vintage", status="error", detail=str(e)))
    out = os.path.join(MAN, "manifest.json")
    json.dump(manifest, open(out, "w"), indent=2)
    ok = sum(1 for r in manifest if r.get("status") == "retrieved")
    blocked = sum(1 for r in manifest if r.get("status") == "blocked_by_egress")
    bad = [r for r in manifest if "MISMATCH" in str(r.get("status"))]
    print(f"retrieved={ok} blocked={blocked} mismatches={len(bad)}")
    for r in manifest:
        if r.get("status") == "retrieved":
            print(f"  {r['source_id']}: {r['bytes']}B sha256={r['sha256'][:16]}... fp_match={r.get('fingerprint_match')}")
    if bad:
        print("FINGERPRINT FAILURES:", [r["source_id"] for r in bad]); sys.exit(1)

if __name__ == "__main__":
    main()
