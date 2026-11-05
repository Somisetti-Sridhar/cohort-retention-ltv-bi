# Retail Observatory — measured findings

US household grocery: 2,469 observed customer identities; 155,368.0 orders; USD 4,596,027.06 positive attributed sales. 91.2% of revenue came after customers' first observed month. 96.1% of 2,447 eligible customers purchased again within 90 days. At-risk customers represent 13.4% of historical revenue; this is not forecast loss.

UK online retail: 5,878 observed customer identities; 36,969.0 orders; GBP 17,374,804.25 positive attributed sales. 82.6% of revenue came after customers' first observed month. 47.3% of 5,281 eligible customers purchased again within 90 days. At-risk customers represent 9.1% of historical revenue; this is not forecast loss.

## Decisions to test

- Test a second-order intervention with a randomized holdout; use the 90-day repeat baseline and distinguish full follow-up from censored customers.
- Prioritize at-risk high-frequency customers for a controlled win-back experiment. Historical revenue is a prioritization signal, not recoverable revenue.
- Audit promotion placement and campaign reach using the natural source keys. Redemption alone does not establish incrementality.

## Verified scale

23,695,261 source records; 2,237,457 retained positive customer-attributed transaction lines; 8 quality gates passed.

## Limits

Historical panels, selection bias, left-censored acquisition, incomplete final months, unknown costs/margins and no marketing spend. This report makes no claims of realized profit uplift, true churn, causal promotion effects, or predicted lifetime value.
