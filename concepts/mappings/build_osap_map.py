#!/usr/bin/env python3
"""Map the 212 OSAP predictors (Chen-Zimmermann SignalDoc) to dictionary concepts.

Dispositions:
  ready          expressible today as a formula/recipe over existing concept_ids
  ready-recipe   expressible, but needs a frozen C2 recipe (regression/rank/interaction),
                 no new data required
  new-concept    needs new concept(s); the DATA already flows from wired/specified
                 sources (EODHD OHLC, XBRL tags, filings via DICT-07)
  partial        framework concepts exist (link.*, own.*, analyst.*) but the mapping
                 depends on populating link/holder/snapshot detail
  blocked-data   honest mapping impossible until a new data source is wired
                 (revision-level estimates, intraday, patents, defunct indices)
"""
import csv
from pathlib import Path

HERE = Path(__file__).resolve().parent

# acronym -> (disposition, concept mapping / expression, note)
M = {
 # ---------------- 13F ----------------
 "Activism1": ("partial", "own.top10_share + own.inst_pct + external-blockholder flag", "holder-level detail exists in Holders map; takeover-vulnerability recipe"),
 "Activism2": ("partial", "own.* holder-level activism screen", "needs holder identity classification (activist list = adhoc dataset)"),
 "DelBreadth": ("partial", "d(own.inst_holder_count) scaled", "13F lag rules (DICT-16) apply; breadth needs consistent holder universe"),
 "IO_ShortInterest": ("ready", "own.inst_pct x raw.short_interest interaction", "both concepts exist (short_interest tier C)"),
 "RIO_Disp": ("blocked-data", "residual own.inst_pct x est.eps_ntm_std", "dispersion leg needs estimates vendor (est.* schema-first)"),
 "RIO_MB": ("ready-recipe", "residual(own.inst_pct | size) x signal.book_to_price", "residual-IO = cross-sectional regression recipe"),
 "RIO_Turnover": ("ready-recipe", "residual(own.inst_pct) x market.turnover", ""),
 "RIO_Volatility": ("ready-recipe", "residual(own.inst_pct) x market.idio_vol", ""),
 # ---------------- Accounting: R&D ----------------
 "AdExp": ("new-concept", "raw.advertising_expense / raw.market_cap", "XBRL AdvertisingExpense; new raw item"),
 "GrAdExp": ("new-concept", "growth(raw.advertising_expense)", "same new raw item"),
 "BrandInvest": ("new-concept", "capitalized raw.advertising_expense recipe", "same"),
 "OrgCap": ("ready-recipe", "capitalized raw.sga perpetual-inventory recipe / raw.total_assets", ""),
 "RD": ("ready", "raw.rnd / raw.market_cap", ""),
 "RDcap": ("ready-recipe", "capitalized raw.rnd (5y PIM) / raw.total_assets", ""),
 "SurpriseRD": ("ready", "unexpected increase in raw.rnd vs trend", ""),
 "RDAbility": ("ready-recipe", "firm-level regression of revenue growth on lagged raw.rnd", ""),
 "RDIPO": ("ready", "action.ipo age join x raw.rnd == 0", ""),
 # ---------------- Accounting: accruals ----------------
 "AbnormalAccruals": ("ready-recipe", "residual of derived.accruals_cf on Jones-model terms (raw.revenue delta, raw.gross_ppe, raw.total_assets) by class.membership", ""),
 "Accruals": ("ready", "derived.accruals_bs", "balance-sheet Sloan accrual is the v1 concept"),
 "OrderBacklogChg": ("new-concept", "d(raw.order_backlog)", "10-K item; DICT-07 extraction, new filing-derived raw"),
 "PctAcc": ("ready", "(raw.net_income - raw.cfo) / abs(raw.net_income)", ""),
 "PctTotAcc": ("ready-recipe", "total accruals incl investing/financing rows / abs(NI)", "uses raw.cfi/raw.cff components"),
 "TotalAccruals": ("ready-recipe", "d(non-cash assets - liabilities) - d(equity) composite", ""),
 # ---------------- Accounting: asset composition ----------------
 "Cash": ("ready", "raw.cash_and_equivalents + raw.short_term_investments / raw.total_assets", ""),
 "NOA": ("ready", "derived.noa", ""),
 "realestate": ("new-concept", "raw.buildings_and_land / raw.gross_ppe", "XBRL PP&E components; new raw item"),
 "tang": ("ready-recipe", "cash + a*receivables + b*inventory + c*ppe weighted liquidation values", "Almeida-Campello weights recipe over existing raws"),
 "VarCF": ("ready", "var(raw.cfo/raw.market_cap, 5y)", ""),
 # ---------------- Accounting: composites ----------------
 "FR": ("ready", "raw.pension_liability / raw.market_cap", "funded status raw exists"),
 "MS": ("new-concept", "indicator.mohanram_g (8 binaries over existing concepts)", "new indicator, inputs all exist"),
 "PS": ("ready", "indicator.f_score", "direct hit"),
 "RDS": ("new-concept", "real dirty surplus: needs raw.oci components", "XBRL OCI tags; new raw item"),
 "OScore": ("ready", "indicator.ohlson_o", "direct hit"),
 # ---------------- Accounting: earnings ----------------
 "PredictedFE": ("blocked-data", "regression needs analyst forecast errors history", "revision-level estimates gate (DICT-15 §3)"),
 "EarningsConsistency": ("ready-recipe", "streak stats over raw.eps_diluted FY history", ""),
 "EarningsStreak": ("ready-recipe", "sign-streak of earnings surprise (est.surprise_last history)", "surprise leg wired tier C"),
 "EarningsSurprise": ("ready", "SUE: d(raw.eps_diluted, 4q) / std(8q)", "seasonal-random-walk form needs no estimates"),
 "NumEarnIncrease": ("ready-recipe", "count of consecutive quarterly eps increases", ""),
 "RevenueSurprise": ("ready", "SUE form over raw.revenue quarterly", ""),
 "EarnSupBig": ("ready-recipe", "big-firm earnings surprise aggregated by class.membership", "lead-lag recipe"),
 # ---------------- Accounting: external financing ----------------
 "CompEquIss": ("ready-recipe", "log growth(raw.market_cap) - cumulative market.ret_1d_tr, 5y", ""),
 "CompositeDebtIssuance": ("ready", "log growth(raw.total_debt, 5y)", ""),
 "ConvDebt": ("new-concept", "raw.convertible_debt indicator", "XBRL convertible tags; new raw item"),
 "DebtIssuance": ("ready", "raw.debt_issued > 0 indicator", ""),
 "DelCOL": ("ready", "d(raw.current_liabilities - raw.short_term_debt) / avg assets", ""),
 "DelFINL": ("ready", "d(raw.total_debt + raw.preferred_equity) / avg assets", ""),
 "NetDebtFinance": ("ready", "(raw.debt_issued - raw.debt_repaid) / avg assets", ""),
 "NetEquityFinance": ("ready", "(raw.share_issuance - raw.share_repurchases) / avg assets", ""),
 "ShareIss1Y": ("ready", "growth(raw.shares_outstanding, 1y) adj for actions (AdjustmentChain)", ""),
 "ShareIss5Y": ("ready", "growth(raw.shares_outstanding, 5y) adj", ""),
 "XFIN": ("ready", "net external financing from raw.cff components / raw.total_assets", ""),
 # ---------------- Accounting: investment ----------------
 "AssetGrowth": ("ready", "signal.asset_growth", "direct hit (sign-inverted)"),
 "ChEQ": ("ready", "growth(raw.common_equity, 1y)", ""),
 "DelEqu": ("ready", "d(raw.common_equity) / avg assets", ""),
 "DelLTI": ("new-concept", "d(raw.long_term_investments)", "new raw item; XBRL LongTermInvestments"),
 "GrLTNOA": ("ready-recipe", "growth in long-term NOA (net_ppe + intangibles - ...)", ""),
 "InvestPPEInv": ("ready", "(d raw.gross_ppe + d raw.inventory) / lag(raw.total_assets)", ""),
 "Investment": ("ready", "raw.capex / raw.revenue vs 3y mean", "= derived.capex_intensity vs trend"),
 "dNoa": ("ready", "d(derived.noa)", ""),
 "ChInv": ("ready", "d(raw.inventory) / avg assets", ""),
 "ChNNCOA": ("ready", "d(noncurrent operating assets - liabilities) / assets", "composes existing raws"),
 "ChNWC": ("ready", "d(raw.working_capital net of cash/debt) / assets", ""),
 "DelCOA": ("ready", "d(raw.current_assets - raw.cash_and_equivalents) / avg assets", ""),
 "DelDRC": ("ready", "d(raw.deferred_revenue) / avg assets", "raw exists"),
 "DelNetFin": ("ready", "d(financial assets - financial liabilities) / avg assets", ""),
 "ChInvIA": ("ready-recipe", "capex+inv growth minus class.membership industry mean", "industry-adjust recipe"),
 "grcapx": ("ready", "growth(raw.capex, 2y)", ""),
 "grcapx3y": ("ready", "growth(raw.capex, 3y)", ""),
 "InvGrowth": ("ready", "growth(raw.inventory, 1y)", ""),
 # ---------------- Accounting: leverage/other ----------------
 "BPEBM": ("ready-recipe", "leverage component of BM decomposition (book/market netdebt split)", ""),
 "BookLeverage": ("ready", "raw.total_assets / raw.common_equity", ""),
 "Leverage": ("ready", "raw.total_debt / raw.market_cap", ""),
 "NetDebtPrice": ("ready", "derived.net_debt / raw.market_cap", ""),
 "IntanBM": ("ready-recipe", "residual of 5y return on d(book) - intangible-return recipe", ""),
 "IntanCFP": ("ready-recipe", "same, cash-flow-to-price version", ""),
 "IntanEP": ("ready-recipe", "same, E/P version", ""),
 "IntanSP": ("ready-recipe", "same, S/P version", ""),
 "ChTax": ("ready", "d(raw.tax_expense, 4q) / lag assets", ""),
 "OPLeverage": ("ready", "(raw.cogs + raw.sga) / raw.total_assets", ""),
 "Tax": ("ready", "taxable income proxy (raw.tax_expense grossed) / raw.net_income", ""),
 "ShareRepurchase": ("ready", "raw.share_repurchases > 0 indicator", ""),
 # ---------------- Accounting: profitability ----------------
 "CBOperProf": ("ready", "cash-based op profit (op profit - accrual deltas) / assets", "all component raws exist"),
 "GP": ("ready", "derived.gpoa", "direct hit"),
 "OperProf": ("ready", "(raw.gross_profit - raw.sga) / raw.common_equity", ""),
 "OperProfRD": ("ready", "op profit + raw.rnd add-back / assets", ""),
 "RoE": ("ready", "derived.roe", "direct hit"),
 "roaq": ("ready", "derived.roa at FQ basis", ""),
 "CashProd": ("ready", "(raw.market_cap + raw.total_debt - raw.total_assets) / cash", ""),
 # ---------------- Accounting: sales growth ----------------
 "ChAssetTurnover": ("ready", "d(raw.revenue / avg raw.total_assets)", ""),
 "GrSaleToGrInv": ("ready", "growth(revenue) - growth(inventory)", ""),
 "GrSaleToGrOverhead": ("ready", "growth(revenue) - growth(raw.sga)", ""),
 "MeanRankRevGrowth": ("ready-recipe", "weighted rank of 5y revenue growth", ""),
 "OrderBacklog": ("new-concept", "raw.order_backlog / avg assets", "same new filing-derived raw as OrderBacklogChg"),
 # ---------------- Accounting: valuation ----------------
 "AM": ("ready", "raw.total_assets / raw.market_cap", ""),
 "AccrualsBM": ("ready-recipe", "signal.book_to_price x derived.accruals_bs interaction", ""),
 "BM": ("ready", "signal.book_to_price", "direct hit"),
 "BMdec": ("ready-recipe", "book_to_price with December market-cap convention (ref calendar)", ""),
 "CF": ("ready", "(raw.net_income + raw.dep_amort) / raw.market_cap", ""),
 "cfp": ("ready", "signal.cfo_yield", "direct hit"),
 "DivYieldST": ("ready-recipe", "predicted next-month dps from event.dividend_declaration pattern", "action/dividend history exists"),
 "EBM": ("ready-recipe", "enterprise component of BM (net-debt-adjusted book/price)", ""),
 "EP": ("ready", "signal.earnings_yield", "direct hit"),
 "EntMult": ("ready", "1 / signal.ebitda_to_ev", "inverse of existing"),
 "EquityDuration": ("ready-recipe", "Dechow duration: forecast CF ladder over concepts", ""),
 "Frontier": ("ready-recipe", "residual of log(M/B) on fundamentals cross-section", ""),
 "NetPayoutYield": ("ready", "signal.shareholder_yield variant incl issuance", "= div + buyback - issuance / mcap"),
 "PayoutYield": ("ready", "(raw.dividends_paid + raw.share_repurchases) / raw.market_cap", ""),
 "SP": ("ready", "signal.sales_to_price", "direct hit"),
 # ---------------- Analyst ----------------
 "ExclExp": ("blocked-data", "GAAP vs street EPS gap", "needs street (IBES-style) actuals"),
 "ChNAnalyst": ("partial", "d(analyst.rating_count or est count)", "snapshot diffs, lag-blurred (DICT-16 caveat)"),
 "AnalystRevision": ("blocked-data", "est.eps_revision_3m", "THE gated concept: revision-level estimates vendor required"),
 "ChForecastAccrual": ("blocked-data", "revision x accrual interaction", "revision leg gated"),
 "DownRecomm": ("partial", "analyst.rating_delta_3m < 0", "snapshot-diff tier C"),
 "UpRecomm": ("partial", "analyst.rating_delta_3m > 0", "same"),
 "EarningsForecastDisparity": ("blocked-data", "LT vs ST forecast gap", "needs fy1/fy2/LTG detail from estimates vendor"),
 "REV6": ("blocked-data", "6m revision aggregate", "gated"),
 "fgr5yrLag": ("blocked-data", "est.ltg_mean (new est concept)", "schema addition; vendor gated"),
 "AOP": ("blocked-data", "analyst value vs price optimism", "needs forecast detail"),
 "CredRatDG": ("new-concept", "credit.issuer_rating downgrade event", "needs issuer-ratings feed; concept + source shopping-list item"),
 "FEPS": ("partial", "est.eps_fy1 (schema exists)", "servable tier C from snapshot when wired"),
 "ChangeInRecommendation": ("partial", "analyst.rating_delta_3m", "snapshot-diff caveat"),
 "ConsRecomm": ("partial", "analyst.rating_mean", "servable now (EODHD, US)"),
 "Recomm_ShortInterest": ("partial", "analyst.rating_mean x raw.short_interest", ""),
 "AnalystValue": ("blocked-data", "forecast-implied value / price", "forecast detail gated"),
 "sfe": ("partial", "est.eps_fy1 / raw.price_close", "snapshot tier C when wired"),
 "ForecastDispersion": ("blocked-data", "est.eps_ntm_std / |mean|", "schema exists; vendor gated"),
 # ---------------- Event ----------------
 "IndIPO": ("ready", "action.ipo recency indicator", ""),
 "AgeIPO": ("ready", "action.ipo + ident age join", ""),
 "ExchSwitch": ("ready", "action.exchange_move recency", ""),
 "Spinoff": ("ready", "action.spinoff recency", ""),
 "DivInit": ("ready", "first action.dividend_cash after >=2y none", ""),
 "DivOmit": ("ready", "expected dividend missed (declaration pattern break)", ""),
 "DivSeason": ("ready-recipe", "predicted ex-month from action.dividend_cash history", ""),
 # ---------------- Options ----------------
 "dCPVolSpread": ("ready", "d(opt call-put IV spread)", "param variant of opt.skew_25d + opt.iv_dlt_1d"),
 "dVolCall": ("ready", "d(call-side IV)", "surface variant, construction exists"),
 "dVolPut": ("ready", "d(put-side IV)", ""),
 "CPVolSpread": ("ready", "-opt.skew_25d (call minus put)", "sign flip of existing"),
 "RIVolSpread": ("ready", "opt.rv_iv_spread", "direct hit"),
 "SmileSlope": ("ready", "opt.skew_25d", "direct hit"),
 "skew1": ("ready", "OTM-put vs ATM-call smirk (param variant of skew)", ""),
 "OptionVolume1": ("new-concept", "opt.volume_ratio = option volume / stock volume", "contract volume is in feed; new concept"),
 "OptionVolume2": ("new-concept", "opt.volume_ratio vs its 6m mean", "same"),
 # ---------------- Other ----------------
 "FirmAge": ("ready", "ident listing-age (first_trade_date join)", ""),
 "hire": ("new-concept", "growth(raw.employees)", "10-K/XBRL employee count; new raw item"),
 "CustomerMomentum": ("partial", "link.exposure(customer) weighted market.momentum", "framework exists; customer links must be populated (filing-derived)"),
 "iomom_cust": ("partial", "customer-industry momentum via link.*", "same"),
 "iomom_supp": ("partial", "supplier-industry momentum via link.*", "same"),
 "Governance": ("blocked-data", "G-index", "underlying index discontinued; adhoc dataset if ever needed"),
 "Herf": ("ready-recipe", "HHI of raw.revenue within class.membership", ""),
 "HerfAsset": ("ready-recipe", "HHI of raw.total_assets within industry", ""),
 "HerfBE": ("ready-recipe", "HHI of raw.common_equity within industry", ""),
 "sinAlgo": ("ready-recipe", "class.membership sin-industry rule set", ""),
 "CitationsRD": ("blocked-data", "patent citations / raw.rnd", "patent dataset = DICT-20 adhoc candidate"),
 "PatentsRD": ("blocked-data", "patents / raw.rnd", "same"),
 # ---------------- Price ----------------
 "AnnouncementReturn": ("ready", "market.ret around event.earnings_date_confirmed window", ""),
 "IndRetBig": ("ready-recipe", "big-firm return by class.membership (lead-lag)", ""),
 "PriceDelayRsq": ("ready-recipe", "weekly ret regression on lagged benchmark (ref.benchmark_map)", ""),
 "PriceDelaySlope": ("ready-recipe", "same, slope form", ""),
 "PriceDelayTstat": ("ready-recipe", "same, t-stat form", ""),
 "retConglomerate": ("partial", "pseudo-conglomerate return via filing_item.segment_revenue + class returns", "segment extraction is tier B/C"),
 "BetaLiquidityPS": ("new-concept", "beta to factor.liquidity_agg (Pastor-Stambaugh)", "needs internal factor-series construction (factor.*)"),
 "LRreversal": ("ready", "cumulative market.ret months 13-36 (window variant)", ""),
 "MRreversal": ("ready", "cumulative ret months 7-12", ""),
 "FirmAgeMom": ("ready-recipe", "market.momentum_12_1 conditioned on ident age", ""),
 "High52": ("ready", "market.distance_52w_high", "direct hit"),
 "IndMom": ("ready-recipe", "class.membership-mean momentum", ""),
 "IntMom": ("ready", "cumulative ret months 7-12 (= MRreversal sign context)", ""),
 "Mom12m": ("ready", "market.momentum_12_1", "direct hit"),
 "Mom6m": ("ready", "market.momentum_6_1", "direct hit"),
 "Mom6mJunk": ("new-concept", "momentum conditioned on credit.issuer_rating", "issuer-ratings feed needed (same as CredRatDG)"),
 "MomRev": ("ready-recipe", "momentum x LT-reversal double sort", ""),
 "MomVol": ("ready-recipe", "momentum within high market.turnover tercile", ""),
 "ResidualMomentum": ("new-concept", "momentum of factor.residual (FF3)", "needs internal factor.* return series"),
 "TrendFactor": ("ready-recipe", "cross-sec regression of ret on MA(price) ensemble", ""),
 "BetaFP": ("ready-recipe", "corr x vol-ratio beta (Frazzini-Pedersen) from market.* pieces", ""),
 "Mom12mOffSeason": ("ready-recipe", "seasonality-purged momentum (monthly ret history)", ""),
 "MomOffSeason": ("ready-recipe", "off-season avg monthly ret", ""),
 "MomOffSeason06YrPlus": ("ready-recipe", "years 6-10 variant", ""),
 "MomOffSeason11YrPlus": ("ready-recipe", "years 11-15 variant", ""),
 "MomOffSeason16YrPlus": ("ready-recipe", "years 16-20 variant", ""),
 "MomSeason": ("ready-recipe", "same-calendar-month avg ret years 2-5", ""),
 "MomSeason06YrPlus": ("ready-recipe", "years 6-10", ""),
 "MomSeason11YrPlus": ("ready-recipe", "years 11-15", ""),
 "MomSeason16YrPlus": ("ready-recipe", "years 16-20", ""),
 "MomSeasonShort": ("ready-recipe", "same-month ret last year", ""),
 "Price": ("ready", "log(raw.price_close)", ""),
 "Beta": ("ready", "market.beta_252d", "direct hit"),
 "BetaTailRisk": ("ready-recipe", "beta to cross-sectional tail-risk index (internal series)", ""),
 "CoskewACX": ("ready-recipe", "daily coskewness vs benchmark", ""),
 "Coskewness": ("ready-recipe", "monthly coskewness vs benchmark", ""),
 "ReturnSkew": ("ready", "market.skew_252d (daily, param window)", ""),
 "ReturnSkew3F": ("new-concept", "skew of factor.residual", "needs factor.* series"),
 "STreversal": ("ready", "market.str_reversal", "direct hit"),
 "Size": ("ready", "log(raw.market_cap)", ""),
 "IdioVol3F": ("new-concept", "idio vol vs FF3 (factor.*)", "market.idio_vol is 1-factor today"),
 "IdioVolAHT": ("ready", "market.idio_vol (CAPM residual variant)", ""),
 "MaxRet": ("ready", "market.max_ret_21d", "direct hit"),
 "RealizedVol": ("ready", "market.vol_252d (param: 1m window)", ""),
 "betaVIX": ("ready-recipe", "ret sensitivity to d(macro.vix)", "both series exist"),
 # ---------------- Trading ----------------
 "BidAskSpread": ("new-concept", "Corwin-Schultz spread from raw.price_high/low", "needs OHLC raws (EODHD has them; DICT-01 gap)"),
 "Illiquidity": ("ready", "market.amihud_illiq", "direct hit"),
 "ProbInformedTrading": ("blocked-data", "PIN from intraday order flow", "microstructure data out of scope v1"),
 "VolSD": ("ready", "std(monthly volume, 36m)", ""),
 "std_turn": ("ready", "std(market.turnover daily, 1m)", ""),
 "zerotrade12M": ("ready", "zero-volume-day count 12m (raw.volume)", ""),
 "zerotrade1M": ("ready", "zero-volume days 1m", ""),
 "zerotrade6M": ("ready", "zero-volume days 6m", ""),
 "ShortInterest": ("ready", "raw.short_interest / raw.shares_outstanding", "tier C source today"),
 "DolVol": ("ready", "market.dollar_volume_63d (param 1m)", "direct hit"),
 "ShareVol": ("ready", "raw.volume mean scaled", ""),
 "VolMkt": ("ready", "dollar volume / raw.market_cap", ""),
 "VolumeTrend": ("ready-recipe", "slope(volume trend) / mean", ""),
}

def main():
    rows = [r for r in csv.DictReader(open(HERE / "osap_signaldoc_2025.csv"))
            if r["Cat.Signal"] == "Predictor"]
    out = []
    missing = []
    for r in rows:
        a = r["Acronym"]
        if a not in M:
            missing.append(a)
            continue
        d, mapping, note = M[a]
        out.append({
            "acronym": a, "description": r["LongDescription"],
            "authors": r["Authors"], "year": r["Year"],
            "cat_data": r["Cat.Data"], "cat_econ": r["Cat.Economic"],
            "disposition": d, "concept_mapping": mapping, "note": note,
        })
    if missing:
        print("UNMAPPED:", missing)
    with open(HERE / "osap_map.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(out[0].keys()))
        w.writeheader(); w.writerows(out)
    import collections
    stats = collections.Counter(o["disposition"] for o in out)
    print(f"{len(out)} predictors mapped -> osap_map.csv")
    for k in ["ready", "ready-recipe", "new-concept", "partial", "blocked-data"]:
        print(f"  {k:14} {stats.get(k,0):3}")

if __name__ == "__main__":
    main()
