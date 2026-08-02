# DICT-06 · Market/price-derived (tier: market)
From adjusted returns (AdjustmentChain) and volume. Validation [V1,V2,V10]; windows in trading days; min-coverage rules per concept (else null+flag).

| concept_id | definition | params |
|---|---|---|
| market.momentum_12_1 | cumulative return t-252..t-21 | classic 12-1; min 200 obs |
| market.momentum_6_1 | t-126..t-21 | |
| market.str_reversal | -return t-21..t | short-term reversal (inverted) |
| market.vol_252d | std(daily returns, 252) × √252 | |
| market.downside_vol | std(negative daily returns, 252) annualized | |
| market.beta_252d | OLS beta vs local benchmark, daily 252 | benchmark map per exchange; shrunk 0.67·β+0.33 variant market.beta_shrunk |
| market.idio_vol | std of residuals vs benchmark (252d) annualized | |
| market.max_ret_21d | max daily return over 21d | lottery (inverted in composites) |
| market.skew_252d | daily return skewness | |
| market.amihud_illiq | mean(|r_d| / dollar_volume_d, 252) | ×1e6 scale; dollar_volume = price×volume |
| market.turnover | mean(volume/shares_outstanding, 63) | |
| market.dollar_volume_63d | mean(price×volume, 63) | liquidity screens |
| market.distance_52w_high | price / max(price, 252) - 1 | |
| market.drawdown_252d | price/rollmax - 1, min over window | |
| market.corr_benchmark_252d | | crowding/diversification uses |
