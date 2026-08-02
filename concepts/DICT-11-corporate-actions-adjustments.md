# DICT-11 · Corporate actions & the AdjustmentChain (tier: event/reference)
The B5 layer made explicit. Raw prices are stored unadjusted forever (DICT-01: `raw.price_close`); every adjusted series is a deterministic function of raw prices + a versioned chain of confirmed actions. [KEY] Vendor-adjusted closes are never ingested as truth — they are V-check material only. Adjustment is computed at read, per asof, so a late-discovered split corrects history via a new chain version, not by mutating prices [PIT].

## 1. Action concepts (event tier; each has candidate -> confirmed lifecycle)
| concept_id | payload | KT rules |
|---|---|---|
| action.split | ratio (new/old), ex_date | KT_announce (announcement) ≠ KT_effective (ex-date); both stored |
| action.dividend_cash | amount/share, ccy, ex/record/pay dates, type{regular, special} | KT = declaration; special dividends adjust, regulars enter total-return only (convention declared per index style; ours: regular = TR-only) |
| action.dividend_stock | ratio | treated as split-like |
| action.spinoff | child entity_id, distribution ratio, value basis | [KEY] hardest case: parent price gaps down legitimately; V4 must net this out (the "net of known corporate actions" join) |
| action.merger | survivor entity_id, terms {cash, stock ratio, mixed} | acquired listing terminates; identity forwarding via DICT-10 survivor() |
| action.rights_issue | subscription ratio, price | dilution adjustment |
| action.buyback_tender | terms | no price adjustment; flows into signal.buyback_yield |
| action.ticker_change / action.exchange_move | old/new | identity events (DICT-10), no price adjustment |
| action.delisting | reason{merger, bankruptcy, voluntary, regulatory}, last_trade_date | [KEY] delisting RETURN convention declared: bankruptcy -> -30% default on missing final print (CRSP-style), merger -> terms value; convention versioned, backtests cite it |
| action.ipo / action.direct_listing | first_trade_date | left edge of every market concept window |

## 2. Lifecycle: candidate -> confirmed
```
vendor A action feed ─┐
vendor B / filings   ─┼-> ActionCandidate {source, payload, KT} -> quorum: 2 independent sources
8-K / press (D-cells)─┘        agree on (type, ex_date, ratio±tol) -> CONFIRMED (enters chain)
                               single-source after grace window -> confirmed_provisional (flag travels)
                               disagreement -> data.quality claim + X2 ticket; NEVER averaged (same policy as DICT-09)
```
Confirmed actions are append-only; a wrong action is superseded by a correction entry (new vintage), history keeps both [PIT].

## 3. AdjustmentChain (runtime class, extends CLASS-03)
```python
class AdjustmentChain:
    def factors(self, listing_id, asof) -> list[AdjFactor]      # multiplicative, ordered by ex_date, built ONLY from actions confirmed with KT <= asof [PIT]
    def adjust(self, raw_prices, mode) -> series                # mode: price_return | total_return
    def version(self, listing_id, asof) -> chain_version        # cited in provenance of every adjusted value
# [KEY] factors(asof=t) uses actions KNOWN at t: a split discovered late means chain v2 differs from v1
# for the same date range — that is correct, and V9 (vintage monotonicity) applies to chains too.
# Failure mode: mixing chain versions inside one panel. Test: late-split fixture, both vintages golden.
class ReturnBuilder:
    def returns(self, listing_id, window, mode, asof) -> series # the ONLY source of `returns(adjusted)` cited by DICT-06
    # delisting handling per action.delisting convention; halts/zero-volume days per DICT-12 calendar
```

## 4. Derived return/adjustment concepts
| concept_id | definition |
|---|---|
| market.ret_1d_pr / market.ret_1d_tr | Daily price-return / total-return from AdjustmentChain (all DICT-06 windows compose these) |
| market.adj_factor_cum | Cumulative adjustment factor at asof (provenance/debug concept) |
| market.delisting_return | Final return per convention above (flag: convention_id) |
| event.action_pending | Bool: candidate action within next 5 trading days (screens can exclude; C2-visible) |

## 5. Validation
| check | method |
|---|---|
| A1 chain-vs-vendor | our adjusted close vs vendor adjusted_close, tol_rel 1e-3; systematic drift -> missing action alert (this is what vendor-adjusted data is FOR) |
| A2 return-spike audit | |ret_1d| > threshold with no confirmed action and no halt -> candidate action probe + V4 flag |
| A3 spinoff conservation | parent + child market caps day-after vs parent day-before within band |
| A4 vintage replay | chain rebuilt at historical asof equals stored chain version (bit-tol) — V9 for chains |
| A5 TR≥PR identity | cumulative TR ≥ PR over any window with nonnegative dividends; violation = factor bug |
