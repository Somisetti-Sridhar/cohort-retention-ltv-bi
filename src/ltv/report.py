"""Build a portable, offline HTML BI report and an evidence-based executive brief."""

from __future__ import annotations

import html
import json
from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.io as pio

from ltv.bi import load_mart

COLORS = ["#176b91", "#ca5848", "#678b52", "#a87825", "#7f6aa3"]


def generate(root: Path = Path("data"), output: Path = Path("reports")) -> None:
    output.mkdir(parents=True, exist_ok=True)
    build = json.loads((root / "build.json").read_text())
    manifest = json.loads((root / "manifest.json").read_text())
    charts = []

    def chart(fig):
        fig.update_layout(
            template="plotly_white",
            font={"family": "Segoe UI, Arial", "size": 13, "color": "#243b50"},
            paper_bgcolor="#ffffff",
            colorway=COLORS,
            margin={"l": 50, "r": 25, "t": 65, "b": 45},
        )
        charts.append(
            pio.to_html(
                fig,
                full_html=False,
                include_plotlyjs=bool(not charts),
                config={"displaylogo": False, "responsive": True},
            )
        )
        return charts[-1]

    def load(name):
        return load_mart(root / "gold" / f"mart_{name}.parquet")

    monthly, cohorts, segments, repeat = map(load, ["monthly", "cohorts", "segments", "repeat"])
    sections = []
    findings = []
    for item in build["summary"]:
        source, currency = item["source"], item["currency"]
        label = {"retail": "UK online retail", "journey": "US household grocery"}[source]
        m = monthly[monthly.source == source]
        c = cohorts[(cohorts.source == source) & cohorts.is_complete_month]
        s = segments[segments.source == source]
        r = repeat[repeat.source == source].iloc[0]
        returning = m.returning_cohort_revenue.sum() / m.revenue.sum()
        risk = s[s.segment == "At risk"].historical_revenue.sum() / s.historical_revenue.sum()
        findings.append(
            f"{label}: {item['customers']:,} observed customer identities; {item['orders']:,} orders; {currency} {item['revenue']:,.2f} positive attributed sales. {returning:.1%} of revenue came after customers' first observed month. {r.repeat_rate_90d:.1%} of {int(r.eligible_customers):,} eligible customers purchased again within 90 days. At-risk customers represent {risk:.1%} of historical revenue; this is not forecast loss."
        )
        heat = c.pivot(index="cohort_month", columns="month_n", values="retention")
        heat.index = pd.to_datetime(heat.index).strftime("%Y-%m")
        fig = px.imshow(
            heat,
            aspect="auto",
            zmin=0,
            zmax=1,
            color_continuous_scale=["#eef4f8", "#86bccb", "#176b91", "#153752"],
            labels={
                "x": "Months since first observed purchase",
                "y": "First observed cohort",
                "color": "Retention",
            },
            title="Who comes back? Completed observation months only",
        )
        fig.update_traces(
            hovertemplate="Cohort %{y}<br>Month %{x}<br>Retention %{z:.1%}<extra></extra>"
        )
        body = chart(fig)
        body += chart(
            px.bar(
                m,
                x="month",
                y=["first_observed_cohort_revenue", "returning_cohort_revenue"],
                title=f"Revenue mix ({currency}) — final month may be partial",
                color_discrete_sequence=COLORS,
            )
        )
        body += chart(
            px.line(
                c,
                x="month_n",
                y="cumulative_revenue_per_customer",
                color=c.cohort_month.astype(str),
                title=f"Observed cumulative revenue / customer ({currency}); not predicted lifetime profit",
            )
        )
        body += chart(
            px.bar(
                s,
                x="historical_revenue",
                y="segment",
                orientation="h",
                title=f"Customer portfolio: historical revenue by RFM segment ({currency})",
                color_discrete_sequence=COLORS,
            )
        )
        sections.append(
            f'<section id="{source}"><h2>{label}</h2><p class="finding">{html.escape(findings[-1])}</p><div class="figures">{body}</div></section>'
        )
    campaigns = load("campaigns")
    campaign_chart = chart(
        px.scatter(
            campaigns,
            x="targeted_households",
            y="household_redemption_rate",
            size="redemptions",
            hover_name="campaign_id",
            title="Campaign reach and household redemption",
            color_discrete_sequence=COLORS,
        )
    )
    promotion = ""
    if (root / "gold/mart_promotions.parquet").exists():
        p = (
            load("promotions")
            .groupby("promotion_status", as_index=False)[
                ["revenue", "transaction_lines", "retail_discount"]
            ]
            .sum()
        )
        promotion = chart(
            px.bar(
                p,
                x="revenue",
                y="promotion_status",
                orientation="h",
                title="US grocery revenue by observed promotion placement (USD)",
                color_discrete_sequence=COLORS,
            )
        )
    sections.append(
        '<section id="marketing"><h2>Marketing and merchandising</h2><p>Real household/campaign and product/store/week joins. Placement association and redemption are descriptive; targeting is not randomized, so these charts do not measure incremental lift or campaign ROI.</p>'
        + campaign_chart
        + promotion
        + "</section>"
    )
    quality = load("quality")
    sections.append(
        '<section id="quality"><h2>Trust the denominator</h2><p>UCI exclusions are mutually exclusive, in priority order: exact duplicates, invalid fields, returns/cancellations, nonpositive lines, unattributed sales. Anonymous sales remain visible here but cannot support customer cohorts. Grocery positive sales use source receipt value, without subtracting discounts again.</p>'
        + quality.to_html(index=False, border=0)
        + f"<p>{len(build['checks'])} quality gates passed. Local build time: {build['elapsed_seconds']} seconds. This is a measured local run, not a distributed benchmark.</p></section>"
    )
    sources = pd.DataFrame(manifest["sources"])[["table", "rows", "bytes", "sha256", "url"]]
    sections.append(
        '<section id="sources"><h2>Source ledger</h2><p>Historical research datasets; no synthetic transactions and no customer links between retailers. The first cohort is left-censored; “first observed” does not prove acquisition. USD and GBP are never combined in business metrics.</p>'
        + sources.to_html(index=False, border=0, render_links=True)
        + "</section>"
    )
    total = sum(x["rows"] for x in manifest["sources"])
    page = """<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Retail Observatory | Retention & customer value</title><style>
    :root{font-family:'Segoe UI',Arial,sans-serif;color:#243b50;background:#edf3f7}body{margin:0}header{background:#153752;color:white;padding:50px max(5vw,20px) 38px}header p{max-width:75ch;color:#d2e4ee}h1{font-size:clamp(30px,5vw,56px);letter-spacing:-1.5px;margin:0 0 20px}h2{font-size:28px}nav{display:flex;flex-wrap:wrap;gap:24px;padding:20px max(5vw,20px);background:white;border-bottom:3px solid #176b91}a{color:#176b91}main{max-width:1400px;margin:auto;padding:20px}section{background:white;padding:30px;margin-bottom:28px;overflow:auto}p{line-height:1.65;max-width:95ch}.finding{border-left:5px solid #176b91;padding-left:20px;font-size:18px}.figures{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:20px}.figures>div:first-child{grid-column:1/-1}table{border-collapse:collapse;font-size:13px;width:100%}td,th{text-align:left;padding:12px;border-bottom:1px solid #dbe4ec;max-width:300px;overflow-wrap:anywhere}footer{padding:30px}a:focus-visible{outline:3px solid #ca5848}@media(max-width:850px){.figures{display:block}section{padding:15px}}@media print{nav{display:none}section{break-before:page}.figures{display:block}}
    </style><header><h1>Retention is a business model.</h1><p>Retail Observatory examines repeat purchasing, observed customer value, and marketing exposure across two real retailers.</p>"""
    page += (
        f'<p>{total:,} source records across {len(manifest["sources"])} tables. Evidence refreshed {html.escape(build["built_at_utc"][:10])}.</p></header><nav><a href="#journey">US grocery</a><a href="#retail">UK retail</a><a href="#marketing">Marketing</a><a href="#quality">Data quality</a><a href="#sources">Sources</a></nav><main>'
        + "".join(sections)
        + "</main><footer>Source attribution: Daqing Chen, UCI Online Retail II (CC BY 4.0); 84.51° / dunnhumby Complete Journey, processed by Brad Boehmke and Steven Mortimer. See DATA_SOURCES.md for access and interpretation.</footer></html>"
    )
    (output / "retail_observatory.html").write_text(page, encoding="utf-8")
    brief = (
        "# Retail Observatory — measured findings\n\n"
        + "\n\n".join(findings)
        + "\n\n## Decisions to test\n\n- Test a second-order intervention with a randomized holdout; use the 90-day repeat baseline and distinguish full follow-up from censored customers.\n- Prioritize at-risk high-frequency customers for a controlled win-back experiment. Historical revenue is a prioritization signal, not recoverable revenue.\n- Audit promotion placement and campaign reach using the natural source keys. Redemption alone does not establish incrementality.\n\n## Verified scale\n\n"
        + f"{total:,} source records; {build['fact_lines']:,} retained positive customer-attributed transaction lines; {len(build['checks'])} quality gates passed.\n\n"
        + "## Limits\n\nHistorical panels, selection bias, left-censored acquisition, incomplete final months, unknown costs/margins and no marketing spend. This report makes no claims of realized profit uplift, true churn, causal promotion effects, or predicted lifetime value.\n"
    )
    (output / "EXECUTIVE_BRIEF.md").write_text(brief, encoding="utf-8")
    (output / "build_evidence.json").write_text(json.dumps(build, indent=2), encoding="utf-8")
    (output / "source_manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(f"Report: {output / 'retail_observatory.html'}")


if __name__ == "__main__":
    generate()
