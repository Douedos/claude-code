# DICT-09 · Vendor mapping layer
The map is data, per (concept, vendor): field binding + transform + unit/currency rules + quirks. Adding a vendor = a mapping file + adapter; zero concept changes.

## Mapping entry schema
```yaml
concept_id: raw.ebit
vendor: eodhd
binding:
  endpoint: fundamentals
  path: Financials.Income_Statement.quarterly.*.operatingIncome
  unit: reported_currency_units          # EODHD: absolute units
  period_key: date; report_key: filing_date   # [PIT] filing_date -> KT; date -> effective period
transform: none | scale(k) | sum(paths) | first_nonnull(paths)
quirks: ["operatingIncome occasionally includes non-recurring items for <sector>: V4 tighter τ"]
crosschecks: [V7 vs computed fallback]
```

## EODHD map highlights (full file in repo)
- Statements: Financials.{Income_Statement, Balance_Sheet, Cash_Flow}.{quarterly, yearly}; KT from filing_date field where present, else acceptance via filings adapter join [KEY: never the period date].
- raw.total_debt: shortLongTermDebtTotal with fallback sum(shortTermDebt, longTermDebtTotal); V7 vs components.
- raw.shares_outstanding: outstandingShares.quarterly with V5 vs SharesStats; market_cap V7 vs vendor MarketCapitalization.
- Prices/actions: EOD endpoint unadjusted + splits/dividends endpoints -> B5 candidates (never vendor-adjusted closes as raw).
- Known quirks ledger lives WITH the map (quirks are facts about a vendor, versioned like code).

## XBRL/SEC map (companyfacts)
Ordered tag chains (first present wins; choice recorded as provenance_flag):
- raw.revenue: [RevenueFromContractWithCustomerExcludingAssessedTax, RevenueFromContractWithCustomerIncludingAssessedTax, Revenues, SalesRevenueNet]
- raw.ebit: [OperatingIncomeLoss] fallback compute
- raw.net_income: [NetIncomeLoss] (parent) vs ProfitLoss (consolidated -> raw.net_income_consolidated)
- raw.total_assets: [Assets]; raw.total_liabilities: [Liabilities] fallback (LiabilitiesAndStockholdersEquity - StockholdersEquity...)
- raw.common_equity: [StockholdersEquity]; total incl NCI: [StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest]
- raw.cash_and_equivalents: [CashAndCashEquivalentsAtCarryingValue, CashCashEquivalentsRestrictedCashAndRestrictedCashEquivalents(flag restricted)]
- raw.long_term_debt: [LongTermDebtNoncurrent, LongTermDebt(minus DebtCurrent)]; raw.short_term_debt: [LongTermDebtCurrent + ShortTermBorrowings + ...sum chain]
- raw.capex: [PaymentsToAcquirePropertyPlantAndEquipment, PaymentsToAcquireProductiveAssets]
- Dimensions: consolidated only (no segment members) unless concept says otherwise; units USD; frames quarterly with duration/instant handling per flow/balance. [KEY] instant-vs-duration misbinding is the #1 XBRL bug — validator: balance concepts must bind instant facts, flows duration facts (hard check).
- KT = accession acceptance datetime (EDGAR), joining B7 rules.

## Cross-vendor policy
Primary vendor per concept (config), others as V6/V7 checks; disagreements beyond tolerance -> data.quality claim + X2 ticket; NEVER silent averaging of vendors.
