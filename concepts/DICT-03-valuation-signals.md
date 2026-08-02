# DICT-03 · Valuation signals (tier: signal)
Cross-sectional signals ready for C1/C2. Validation [V1,V2,V7,V10]; all use KT-aligned fundamentals over current market data (mixed-KT is the design: latest knowable accounting vs today's price). Yield form preferred over multiple form (E/P not P/E) for well-behaved cross-sections through zero.

| concept_id | formula | notes |
|---|---|---|
| signal.earnings_yield | net_income(TTM) / market_cap | HIS EXAMPLE — worked YAML; diluted variant signal.earnings_yield_diluted = eps_diluted(TTM)/price |
| signal.earnings_yield_fwd | consensus_eps_ntm / price | tier C until estimates vendor wired (DICT-08) |
| signal.book_to_price | common_equity / market_cap | negative book -> null+flag; intangible-adjusted variant: (common_equity - goodwill)/market_cap |
| signal.sales_to_price | revenue(TTM) / market_cap | |
| signal.cfo_yield | cfo(TTM) / market_cap | |
| signal.fcf_yield | fcf(TTM) / market_cap | |
| signal.ebitda_to_ev | ebitda(TTM) / enterprise_value | ev<=0 -> null+flag |
| signal.ebit_to_ev | ebit(TTM) / enterprise_value | |
| signal.dividend_yield | dividends_paid(TTM)/market_cap; per-share variant dps/price | |
| signal.buyback_yield | (share_repurchases - share_issuance)(TTM) / market_cap | |
| signal.shareholder_yield | dividend_yield + buyback_yield | |
| signal.debt_paydown_yield | (debt_repaid - debt_issued)(TTM) / market_cap | total-yield family |
| signal.value_composite | rank-avg of {earnings_yield, book_to_price, cfo_yield, ebitda_to_ev} | C2 recipe, weights config |
