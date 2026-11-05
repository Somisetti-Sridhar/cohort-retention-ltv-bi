// Create a text parameter GoldFolder first; include a trailing slash.
// Name this function LoadGold.
(TableName as text) as table =>
let
    Raw = Csv.Document(File.Contents(GoldFolder & TableName & ".csv"),
        [Delimiter=",", Encoding=65001, QuoteStyle=QuoteStyle.Csv]),
    Headers = Table.PromoteHeaders(Raw, [PromoteAllScalars=true])
in Headers

// Create separate blank queries with the following expressions:
// mart_monthly:
// = Table.TransformColumnTypes(LoadGold("mart_monthly"), {{"month",type date},{"orders",Int64.Type},{"active_customers",Int64.Type},{"revenue",Currency.Type},{"first_observed_cohort_revenue",Currency.Type},{"returning_cohort_revenue",Currency.Type},{"is_complete_month",type logical}},"en-US")
// mart_cohorts:
// = Table.TransformColumnTypes(LoadGold("mart_cohorts"), {{"cohort_month",type date},{"activity_month",type date},{"month_n",Int64.Type},{"cohort_size",Int64.Type},{"active_customers",Int64.Type},{"revenue",Currency.Type},{"retention",type number},{"cumulative_revenue_per_customer",type number},{"is_complete_month",type logical},{"is_left_censored_cohort",type logical}},"en-US")
// mart_segments:
// = Table.TransformColumnTypes(LoadGold("mart_segments"), {{"customers",Int64.Type},{"historical_revenue",Currency.Type},{"mean_recency_days",type number},{"mean_orders",type number}},"en-US")
// mart_repeat:
// = Table.TransformColumnTypes(LoadGold("mart_repeat"), {{"eligible_customers",Int64.Type},{"repeated_90d",Int64.Type},{"repeat_rate_90d",type number}},"en-US")
// mart_campaigns:
// = Table.TransformColumnTypes(LoadGold("mart_campaigns"), {{"targeted_households",Int64.Type},{"redeeming_households",Int64.Type},{"redemptions",Int64.Type},{"household_redemption_rate",type number}},"en-US")
// mart_promotions:
// = Table.TransformColumnTypes(LoadGold("mart_promotions"), {{"week",Int64.Type},{"transaction_lines",Int64.Type},{"baskets",Int64.Type},{"revenue",Currency.Type},{"retail_discount",Currency.Type}},"en-US")
// mart_quality:
// = Table.TransformColumnTypes(LoadGold("mart_quality"), {{"rows",Int64.Type},{"signed_source_value",Currency.Type}},"en-US")
// mart_products:
// = Table.TransformColumnTypes(LoadGold("mart_products"), {{"customers",Int64.Type},{"orders",Int64.Type},{"revenue",Currency.Type},{"retail_discount",Currency.Type},{"coupon_discount",Currency.Type}},"en-US")
