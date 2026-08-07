#!/usr/bin/env python3
"""Parse concepts/DICT-*.md into a concept graph JSON for the explorer app.

Extraction is heuristic by design: concept ids come from table first-columns and
worked YAMLs; edges come from explicit formula/inputs text plus bare-name matches
(e.g. `net_income(TTM)` -> raw.net_income) inside formula-like fields only.
"""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

ID_RE = re.compile(r"\b([a-z][a-z0-9_]*(?:\.[a-z0-9_]+)+)\b")

# namespaces we accept as concept ids (filters out file names, yaml keys, urls)
NAMESPACES = {
    "raw", "derived", "signal", "indicator", "filing", "filing_item", "market",
    "macro", "event", "est", "ident", "action", "ref", "fx", "class", "universe",
    "meta", "own", "insider", "analyst", "esg", "news", "opt", "sov", "credit",
    "rates", "country", "cmdty", "trade", "freight", "product", "link", "adhoc",
    "dal", "data", "factor",
}

FILE_META = {
    "DICT-01": ("Raw statement items", "content"),
    "DICT-02": ("Derived fundamentals", "content"),
    "DICT-03": ("Valuation signals", "content"),
    "DICT-04": ("Quality & growth", "content"),
    "DICT-05": ("Solvency & credit indicators", "content"),
    "DICT-06": ("Market / price-derived", "content"),
    "DICT-07": ("Filing & text items", "content"),
    "DICT-08": ("Estimates, events, macro", "content"),
    "DICT-09": ("Vendor mapping layer", "layer"),
    "DICT-10": ("Entity & identity", "layer"),
    "DICT-11": ("Corporate actions & adjustments", "layer"),
    "DICT-12": ("Reference data & universes", "layer"),
    "DICT-13": ("DAL service contract", "layer"),
    "DICT-14": ("Adapter & vendor ops", "layer"),
    "DICT-15": ("EODHD capability audit", "vendor"),
    "DICT-16": ("Ownership, insiders, analysts, ESG", "content"),
    "DICT-17": ("News & sentiment", "content"),
    "DICT-18": ("Options-implied", "content"),
    "DICT-19": ("Credit, rates, sovereign, country", "content"),
    "DICT-20": ("Ad-hoc & long-tail framework", "layer"),
    "DICT-21": ("Commodities, trade, product", "content"),
    "DICT-22": ("OSAP alpha-catalog mapping", "vendor"),
    "DICT-WORKED": ("Worked examples", "content"),
}

NS_TIER = {
    "raw": "raw", "derived": "derived", "signal": "signal", "indicator": "indicator",
    "filing": "filing", "filing_item": "filing", "market": "market", "opt": "market",
    "macro": "macro", "rates": "macro", "sov": "macro", "credit": "macro",
    "country": "macro", "fx": "macro", "cmdty": "adhoc", "trade": "adhoc",
    "freight": "adhoc", "product": "adhoc", "adhoc": "adhoc",
    "event": "event", "action": "event", "est": "est",
    "ident": "reference", "ref": "reference", "class": "reference",
    "universe": "reference", "link": "reference",
    "own": "ownership", "insider": "ownership", "analyst": "ownership", "esg": "ownership",
    "news": "news", "meta": "meta", "data": "meta", "dal": "meta", "factor": "market",
}


def clean_id(tok: str) -> str | None:
    tok = re.sub(r"\{[^}]*\}", "", tok).strip(" .`")
    if not ID_RE.fullmatch(tok):
        return None
    ns = tok.split(".")[0]
    if ns not in NAMESPACES:
        return None
    # crude yaml-key / prose filters
    if tok.endswith((".yaml", ".md")) or ".quarterly" in tok or "Financials" in tok:
        return None
    return tok


def md_cells(line: str) -> list[str]:
    if not line.strip().startswith("|"):
        return []
    return [c.strip() for c in line.strip().strip("|").split("|")]


def main() -> None:
    concepts: dict[str, dict] = {}
    order: list[str] = []

    def add(cid, file_key, definition="", formula="", notes=""):
        if cid not in concepts:
            concepts[cid] = {
                "id": cid, "file": file_key,
                "tier": NS_TIER.get(cid.split(".")[0], "meta"),
                "def": definition, "formula": formula, "notes": notes,
            }
            order.append(cid)
        else:
            c = concepts[cid]
            if definition and len(definition) > len(c["def"]):
                c["def"] = definition
            if formula and not c["formula"]:
                c["formula"] = formula
            if notes and not c["notes"]:
                c["notes"] = notes

    for path in sorted(ROOT.glob("DICT-*.md")):
        key = "-".join(path.name.split("-")[:2])
        if key not in FILE_META and not path.name.startswith("DICT-WORKED"):
            continue
        text = path.read_text()
        if path.name.startswith("DICT-WORKED"):
            # worked examples: enrich defs/formulas of yaml-declared concepts
            for m in re.finditer(
                r"concept_id:\s*([a-z0-9_.]+).*?(?=\n## |\Z)", text, re.S
            ):
                cid = clean_id(m.group(1))
                if not cid:
                    continue
                block = m.group(0)
                d = re.search(r"definition:\s*>?\s*\n?((?:\s{2,}.+\n)+)", block)
                f = re.search(r"formula:\s*(.+)", block)
                add(cid, concepts.get(cid, {}).get("file", "DICT-WORKED"),
                    definition=re.sub(r"\s+", " ", d.group(1)).strip() if d else "",
                    formula=f.group(1).strip() if f else "")
            continue

        for line in text.splitlines():
            cells = md_cells(line)
            if len(cells) < 2 or set(cells[0]) <= {"-", " ", ":"}:
                continue
            first = cells[0]
            if first.lower() in {"concept_id", "concept", "v", "i", "check", "endpoint(s)",
                                 "level", "stage", "rule", "data", "dictionary domain",
                                 "file", "endpoint"}:
                continue
            # split multi-id cells: "a / b" or "a, b"
            ids = []
            for part in re.split(r"\s*/\s*|\s*,\s*", first):
                cid = clean_id(part.split()[0] if part.split() else "")
                if cid:
                    ids.append(cid)
            if not ids:
                continue
            definition = cells[1] if len(cells) > 1 else ""
            # DICT-02/03/04 style: | id | formula | notes |
            formula, notes = "", ""
            if key in {"DICT-02", "DICT-03", "DICT-04", "DICT-05", "DICT-16",
                       "DICT-17", "DICT-18", "DICT-19", "DICT-21"} and len(cells) >= 2:
                low = definition
                if re.search(r"[/×+\-*]| avg| sum|slope|std\(|CAGR|log\(|mean\(", low):
                    formula, definition = low, ""
                if len(cells) >= 3:
                    notes = cells[2]
                    if not definition:
                        definition = notes if not formula else ""
            for cid in ids:
                add(cid, key, definition=definition, formula=formula, notes=notes)

    # ---- edges ----
    # bare-name map: suffix -> id (prefer raw., then derived., then others)
    suffix: dict[str, str] = {}
    for pref in ["raw", "derived", "signal", "indicator", "market", "macro", "est",
                 "filing_item", "event", "news", "opt", "cmdty", "trade", "product",
                 "own", "insider", "analyst", "esg", "universe", "ident", "action"]:
        for cid in order:
            ns, _, rest = cid.partition(".")
            if ns == pref and rest not in suffix:
                suffix[rest] = cid

    edges: set[tuple[str, str]] = set()
    word_re = re.compile(r"\b([a-z][a-z0-9_]{2,})\b")

    def known(tok: str) -> str | None:
        # trim trailing segments until a known concept id matches (insider.txn.value -> insider.txn)
        parts = tok.split(".")
        while len(parts) >= 2:
            cand = ".".join(parts)
            if cand in concepts:
                return cand
            parts.pop()
        return None

    for cid in order:
        c = concepts[cid]
        srctext = " ".join([c["formula"], c["def"], c["notes"]])
        # explicit dotted ids anywhere
        for m in ID_RE.finditer(srctext):
            tgt = clean_id(m.group(1))
            tgt = known(tgt) if tgt else None
            if tgt and tgt != cid:
                edges.add((cid, tgt))
        # bare names only in formula-like text
        if c["formula"]:
            for m in word_re.finditer(c["formula"]):
                w = m.group(1)
                if w in {"avg", "sum", "std", "mean", "max", "min", "log", "abs",
                         "lag", "slope", "rank", "ttm", "fy", "fq", "cagr"}:
                    continue
                tgt = suffix.get(w)
                if tgt and tgt != cid:
                    edges.add((cid, tgt))

    # curated edges for composites whose formulas use shorthand (X1..X5, F components,
    # window functions over prices) that text heuristics can't see
    MANUAL = [
        ("indicator.altman_z", ["raw.working_capital", "raw.total_assets", "raw.retained_earnings",
                                "raw.ebit", "raw.market_cap", "raw.total_liabilities", "raw.revenue"]),
        ("indicator.altman_z2", ["raw.working_capital", "raw.total_assets", "raw.retained_earnings",
                                 "raw.ebit", "raw.common_equity", "raw.total_liabilities"]),
        ("indicator.ohlson_o", ["raw.total_assets", "raw.total_liabilities", "raw.working_capital",
                                "raw.current_liabilities", "raw.current_assets", "raw.net_income",
                                "raw.ffo", "macro.gdp_deflator"]),
        ("indicator.merton_dd", ["raw.market_cap", "market.vol_252d", "raw.short_term_debt",
                                 "raw.long_term_debt", "macro.ust_3m"]),
        ("indicator.merton_pd", ["indicator.merton_dd"]),
        ("indicator.ohlson_p", ["indicator.ohlson_o"]),
        ("indicator.altman_zone", ["indicator.altman_z"]),
        ("indicator.f_score", ["derived.roa", "raw.cfo", "raw.net_income", "derived.leverage_assets",
                               "indicator.current_ratio", "raw.share_issuance", "derived.gross_margin",
                               "raw.revenue", "raw.total_assets"]),
        ("indicator.solvency_composite", ["indicator.altman_z", "indicator.ohlson_p",
                                          "indicator.merton_dd", "indicator.interest_coverage"]),
        ("insider.net_buy_ratio_6m", ["insider.txn"]),
        ("insider.buyer_breadth_6m", ["insider.txn"]),
        ("insider.officer_buy_flag", ["insider.txn"]),
        ("insider.sell_pressure", ["insider.txn", "own.insider_pct", "raw.market_cap"]),
        ("macro.surprise", ["event.macro_release"]),
        ("macro.surprise_index", ["macro.surprise"]),
        ("news.sent_1d", ["news.item", "news.novelty"]),
        ("news.sent_21d", ["news.sent_1d"]),
        ("news.sent_shock", ["news.sent_1d", "news.sent_21d"]),
        ("news.volume_1d", ["news.item", "news.novelty"]),
        ("news.novelty", ["news.item"]),
        ("news.polarity_d4", ["news.item"]),
        ("news.polarity_vendor", ["news.item"]),
        ("news.event_class", ["news.item"]),
        ("opt.iv_rank_252d", ["opt.iv_atm_30d"]),
        ("opt.rv_iv_spread", ["market.vol_252d", "opt.iv_atm_30d"]),
        ("opt.earnings_iv_ratio", ["event.earnings_date_confirmed"]),
        ("opt.iv_dlt_1d", ["opt.iv_atm_30d"]),
        ("market.momentum_12_1", ["market.ret_1d_tr"]),
        ("market.momentum_6_1", ["market.ret_1d_tr"]),
        ("market.str_reversal", ["market.ret_1d_tr"]),
        ("market.vol_252d", ["market.ret_1d_tr"]),
        ("market.downside_vol", ["market.ret_1d_tr"]),
        ("market.beta_252d", ["market.ret_1d_tr", "ref.benchmark_map"]),
        ("market.idio_vol", ["market.ret_1d_tr", "ref.benchmark_map"]),
        ("market.amihud_illiq", ["market.ret_1d_tr", "raw.price_close", "raw.volume"]),
        ("market.turnover", ["raw.volume", "raw.shares_outstanding"]),
        ("market.dollar_volume_63d", ["raw.price_close", "raw.volume"]),
        ("market.distance_52w_high", ["raw.price_close"]),
        ("market.drawdown_252d", ["raw.price_close"]),
        ("market.ret_1d_pr", ["raw.price_close", "market.adj_factor_cum"]),
        ("market.ret_1d_tr", ["raw.price_close", "market.adj_factor_cum", "action.dividend_cash"]),
        ("market.adj_factor_cum", ["action.split", "action.spinoff", "action.dividend_cash"]),
        ("market.delisting_return", ["action.delisting"]),
        ("universe.investable_v1", ["ident.primary_listing", "raw.price_close",
                                    "market.dollar_volume_63d", "event.action_pending", "universe.coverage"]),
        ("event.guidance_event", ["filing_item.guidance_revision"]),
        ("indicator.going_concern_flag", ["filing_item.going_concern"]),
        ("est.surprise_last", ["est.eps_ntm_mean", "event.earnings_date_confirmed"]),
        ("est.eps_revision_3m", ["est.eps_ntm_mean"]),
        ("signal.earnings_yield_fwd", ["est.eps_ntm_mean", "raw.price_close"]),
        ("cmdty.trend_63d", ["cmdty.spot"]),
        ("cmdty.vol_252d", ["cmdty.spot"]),
        ("cmdty.regime", ["cmdty.spot"]),
        ("cmdty.basket", ["cmdty.spot"]),
        ("trade.balance", ["trade.exports_usd", "trade.imports_usd"]),
        ("trade.yoy", ["trade.exports_usd", "trade.imports_usd", "trade.lane_usd"]),
        ("trade.mirror_gap", ["trade.lane_usd"]),
        ("product.price_cut_flag", ["product.street_price", "product.msrp"]),
        ("product.entity_mix", ["product.catalog", "link.exposure"]),
        ("filing_item.risk_factor_novelty", ["filing.10k.item1a_risk_factors"]),
        ("filing_item.mdna_tone", ["filing.10k.item7_mdna"]),
        ("filing_item.going_concern", ["filing.10k.item8_financials"]),
        ("filing_item.debt_maturity_ladder", ["filing.footnote.debt_schedule"]),
        ("filing_item.segment_revenue", ["filing.footnote.segments"]),
        ("filing_item.guidance_revision", ["filing.8k.item_code"]),
        ("filing_item.restatement_flag", ["filing.8k.item_code"]),
        ("filing_item.auditor_change", ["filing.8k.item_code"]),
    ]
    for src, tgts in MANUAL:
        if src in concepts:
            for t in tgts:
                if t in concepts and t != src:
                    edges.add((src, t))

    out = {
        "version": "1.3",
        "files": {k: {"title": v[0], "group": v[1]} for k, v in FILE_META.items()},
        "concepts": [concepts[c] for c in order],
        "edges": sorted(edges),
    }
    dest = ROOT / "explorer" / "graph.json"
    dest.write_text(json.dumps(out, indent=1))
    print(f"{len(order)} concepts, {len(edges)} edges -> {dest}")
    tiers = {}
    for c in concepts.values():
        tiers[c["tier"]] = tiers.get(c["tier"], 0) + 1
    print(sorted(tiers.items(), key=lambda kv: -kv[1]))


if __name__ == "__main__":
    sys.exit(main())
