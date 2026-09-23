from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path

import pandas as pd
import streamlit as st

from swiss_company_intel.analyzer import CompanyAnalyzer
from swiss_company_intel.config import score_weights_from_mapping
from swiss_company_intel.dashboard_logic import filter_report
from swiss_company_intel.io import load_companies
from swiss_company_intel.models import ScoreWeights
from swiss_company_intel.providers.bfs import BFSClient, ENTERPRISE_STATISTICS


DEFAULT_DATA = Path("data/sample_companies.csv")


def _load_input(uploaded_file) -> pd.DataFrame:
    if uploaded_file is None:
        return load_companies(DEFAULT_DATA)

    raw = pd.read_csv(uploaded_file)
    temp = Path(".streamlit_uploaded_companies.csv")
    raw.to_csv(temp, index=False)
    try:
        return load_companies(temp)
    finally:
        temp.unlink(missing_ok=True)


def main() -> None:
    st.set_page_config(
        page_title="Swiss Company Intelligence",
        page_icon="🇨🇭",
        layout="wide",
    )

    st.title("Swiss Company Intelligence 🇨🇭")
    st.caption(
        "Explainable company screening with Python, sector-relative anomaly detection "
        "and optional official Swiss FSO metadata."
    )

    with st.sidebar:
        st.header("Portfolio")
        uploaded = st.file_uploader("Upload a company CSV", type=["csv"])
        uploaded_weights = st.file_uploader(
            "Optional scoring weights JSON",
            type=["json"],
            key="score-weights",
        )
        top_n = st.slider("Companies to display", min_value=3, max_value=20, value=10)
        st.info("The bundled dataset is synthetic and intended for software demonstration.")

    try:
        companies = _load_input(uploaded)
        if uploaded_weights is None:
            weights = ScoreWeights()
        else:
            payload = json.loads(uploaded_weights.getvalue().decode("utf-8"))
            if not isinstance(payload, dict):
                raise ValueError("Score weights configuration must be a JSON object")
            weights = score_weights_from_mapping(payload)

        analyzer = CompanyAnalyzer(weights)
        analyzed = analyzer.analyze(companies)
        report = analyzer.report_columns(analyzed)
    except Exception as exc:
        st.error(f"Could not analyze the dataset: {exc}")
        st.stop()

    with st.sidebar:
        with st.expander("Active scoring weights"):
            st.json(asdict(weights))

        st.header("Filters")
        selected_cantons = st.multiselect(
            "Canton",
            options=sorted(report["canton"].unique()),
        )
        selected_sectors = st.multiselect(
            "Sector",
            options=sorted(report["sector"].unique()),
        )
        selected_bands = st.multiselect(
            "Priority band",
            options=["low", "moderate", "high", "critical"],
        )

    filtered_report = filter_report(
        report,
        cantons=selected_cantons,
        sectors=selected_sectors,
        priority_bands=selected_bands,
    )

    if filtered_report.empty:
        st.warning("No companies match the selected filters.")
        st.stop()

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Companies", len(filtered_report))
    c2.metric("Sectors", filtered_report["sector"].nunique())
    c3.metric("Average attention", f"{filtered_report['attention_score'].mean():.1f}")
    c4.metric(
        "High / critical",
        int(filtered_report["priority_band"].isin(["high", "critical"]).sum()),
    )

    st.subheader("Company drill-down")
    selected_company = st.selectbox(
        "Select a company",
        options=filtered_report["company"].tolist(),
    )
    company = filtered_report.loc[
        filtered_report["company"] == selected_company
    ].iloc[0]

    d1, d2, d3, d4 = st.columns(4)
    d1.metric("Attention score", f"{company['attention_score']:.1f}")
    d2.metric("Priority", str(company["priority_band"]).title())
    d3.metric("Revenue growth", f"{company['revenue_growth_pct']:.1f}%")
    d4.metric("Debt / equity", f"{company['debt_to_equity']:.2f}x")
    st.write(f"**Why it was flagged:** {company['reasons']}")

    st.subheader("Attention ranking")
    st.dataframe(
        filtered_report.head(top_n),
        use_container_width=True,
        hide_index=True,
    )

    st.subheader("Attention score by company")
    chart = filtered_report.head(top_n).set_index("company")[["attention_score"]]
    st.bar_chart(chart)

    st.subheader("Sector overview")
    sector_summary = (
        filtered_report.groupby("sector", as_index=False)
        .agg(
            companies=("company", "count"),
            avg_attention=("attention_score", "mean"),
            avg_growth=("revenue_growth_pct", "mean"),
        )
        .sort_values("avg_attention", ascending=False)
    )
    st.dataframe(sector_summary, use_container_width=True, hide_index=True)

    st.divider()
    st.subheader("Official Swiss FSO / BFS connection")
    st.write(
        "The project includes a provider for the Federal Statistical Office STAT-TAB "
        "PxWeb API. This keeps official-data access separate from the scoring engine."
    )

    if st.button("Load official enterprise-statistics metadata"):
        with st.spinner("Contacting the Federal Statistical Office..."):
            try:
                client = BFSClient()
                metadata = client.get_metadata()
                st.success(f"Connected to FSO cube: {ENTERPRISE_STATISTICS.name}")
                st.caption(metadata.get("title", ENTERPRISE_STATISTICS.description))
                variables = pd.DataFrame(client.variable_summary(metadata))
                st.dataframe(variables, use_container_width=True, hide_index=True)
            except Exception as exc:
                st.warning(
                    "The live FSO endpoint could not be reached from this environment. "
                    f"The local analysis still works normally. Details: {exc}"
                )

    st.caption(
        "Attention scores are transparent screening heuristics, not credit ratings "
        "or investment advice."
    )


if __name__ == "__main__":
    main()
