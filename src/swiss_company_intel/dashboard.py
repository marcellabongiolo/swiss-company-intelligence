from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path
from tempfile import TemporaryDirectory

import pandas as pd
import streamlit as st

from swiss_company_intel.analyzer import CompanyAnalyzer
from swiss_company_intel.config import score_weights_from_mapping
from swiss_company_intel.dashboard_logic import filter_report, history_chart_data, report_to_csv_bytes
from swiss_company_intel.io import load_companies, validate_companies
from swiss_company_intel.models import ScoreWeights
from swiss_company_intel.persistence import AnalysisStore
from swiss_company_intel.providers.bfs import BFSClient, ENTERPRISE_STATISTICS


DEFAULT_DATA = Path("data/sample_companies.csv")
def _session_store() -> AnalysisStore:
    """Keep each browser session's history in its own temporary directory."""
    key = "_analysis_history_directory"
    if key not in st.session_state:
        st.session_state[key] = TemporaryDirectory(prefix="swiss-intel-session-")
    directory = st.session_state[key]
    return AnalysisStore(Path(directory.name) / "history.db")


def _load_input(uploaded_file) -> pd.DataFrame:
    if uploaded_file is None:
        return load_companies(DEFAULT_DATA)

    return validate_companies(pd.read_csv(uploaded_file))


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

    st.info(
        "🇨🇭 **O que este site faz?** Ele compara indicadores financeiros e operacionais "
        "de empresas suíças e destaca quais merecem uma análise mais cuidadosa. "
        "**Não é uma previsão de falência nem uma recomendação de investimento.**"
    )
    st.warning(
        "Os dados financeiros das empresas no exemplo são **sintéticos (inventados)**. "
        "Os nomes das empresas não representam resultados financeiros reais."
    )
    with st.expander("📖 Como usar o painel — guia rápido", expanded=True):
        st.markdown(
            "1. **Comece pelo exemplo:** o painel já carrega uma planilha fictícia. "
            "Não é necessário enviar arquivos.\\n"
            "2. **Veja a pontuação de atenção (0–100):** quanto maior, mais sinais "
            "merecem investigação. Isso não é uma nota de qualidade da empresa.\\n"
            "3. **Escolha uma empresa** em *Company drill-down* para entender "
            "os indicadores e os motivos da sinalização.\\n"
            "4. **Use os filtros na barra lateral** para pesquisar por empresa, "
            "cantão, setor ou prioridade.\\n"
            "5. **Compare os gráficos** e baixe o CSV com os resultados filtrados."
        )
        st.caption(
            "Termos úteis: cantão = divisão administrativa suíça; setor = ramo "
            "de atividade; benchmark = comparação com empresas semelhantes; "
            "anomalia = valor incomum que merece verificação."
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
        company_query = st.text_input("Search company name", placeholder="Company name")
        selected_cantons = st.multiselect(
            "Canton",
            options=sorted(report["canton"].unique()),
        )
        selected_sectors = st.multiselect(
            "Sector",
            options=sorted(report["sector"].unique()),
        )
        min_attention_score = st.slider("Minimum attention score", 0, 100, 0)
        selected_bands = st.multiselect(
            "Priority band",
            options=["low", "moderate", "high", "critical"],
        )

    filtered_report = filter_report(
        report,
        cantons=selected_cantons,
        sectors=selected_sectors,
        priority_bands=selected_bands,
        company_query=company_query,
        min_attention_score=min_attention_score,
    )

    if filtered_report.empty:
        st.warning("No companies match the selected filters.")
        st.stop()

    st.download_button(
        "Download filtered results (CSV)",
        data=report_to_csv_bytes(filtered_report),
        file_name="swiss_company_filtered_report.csv",
        mime="text/csv",
    )

    store = _session_store()
    st.caption("Saved snapshots are private to this browser session and temporary.")

    save_col, history_col = st.columns([1, 2])
    with save_col:
        if st.button("Save analysis snapshot"):
            run_id = store.save_analysis(report, source="streamlit")
            st.success(f"Saved analysis run #{run_id}")

    with history_col:
        recent_runs = store.list_runs(limit=5)
        if not recent_runs.empty:
            st.caption(f"Saved runs: {len(recent_runs)} shown")
            with st.expander("Browse saved analysis runs"):
                st.dataframe(recent_runs, use_container_width=True, hide_index=True)
                selected_run_id = st.selectbox(
                    "View saved run",
                    options=recent_runs["id"].astype(int).tolist(),
                    format_func=lambda run_id: f"Run #{run_id}",
                )
                saved_report = store.run_details(selected_run_id)
                st.dataframe(
                    saved_report,
                    use_container_width=True,
                    hide_index=True,
                )
                st.download_button(
                    "Download saved run (CSV)",
                    data=report_to_csv_bytes(saved_report),
                    file_name=f"swiss_company_run_{selected_run_id}.csv",
                    mime="text/csv",
                    key=f"download-run-{selected_run_id}",
                )

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Companies", len(filtered_report))
    c2.metric("Sectors", filtered_report["sector"].nunique())
    c3.metric("Average attention", f"{filtered_report['attention_score'].mean():.1f}")
    c4.metric(
        "High / critical",
        int(filtered_report["priority_band"].isin(["high", "critical"]).sum()),
    )

    st.caption("Interpretação: pontuação mais alta = maior prioridade de revisão, não maior risco comprovado.")

    st.subheader("🧭 Visão geral: prioridades de análise")
    st.caption(
        "Pontuações mais altas significam mais sinais para investigar, não uma "
        "probabilidade de falência. Os dados das empresas são fictícios."
    )
    band_order = ["low", "moderate", "high", "critical"]
    band_names = {
        "low": "Baixa", "moderate": "Moderada",
        "high": "Alta", "critical": "Crítica",
    }
    distribution = (
        filtered_report["priority_band"].value_counts()
        .reindex(band_order, fill_value=0)
        .rename(index=band_names)
    )
    chart_left, chart_right = st.columns(2)
    with chart_left:
        st.markdown("**Empresas por nível de atenção**")
        st.bar_chart(distribution)
    with chart_right:
        st.markdown("**Atenção média por setor**")
        sector_attention = (
            filtered_report.groupby("sector")["attention_score"]
            .mean().sort_values(ascending=False)
        )
        st.bar_chart(sector_attention)
    st.markdown("**Cinco empresas com maior prioridade de revisão**")
    st.dataframe(
        filtered_report.nlargest(5, "attention_score")[
            ["company", "sector", "canton", "attention_score", "priority_band", "reasons"]
        ],
        use_container_width=True,
        hide_index=True,
    )

    st.subheader("⚖️ Comparador de empresas")
    st.caption("Compare indicadores de duas empresas do conjunto filtrado.")
    options = filtered_report["company"].drop_duplicates().tolist()
    if len(options) < 2:
        st.info("Selecione pelo menos duas empresas nos filtros para comparar.")
    else:
        first, second = st.columns(2)
        with first:
            company_a = st.selectbox("Empresa A", options, index=0, key="compare-a")
        with second:
            company_b = st.selectbox("Empresa B", options, index=1, key="compare-b")
        if company_a == company_b:
            st.warning("Escolha duas empresas diferentes.")
        else:
            compare_columns = {
                "attention_score": "Pontuação de atenção (0–100)",
                "revenue_growth_pct": "Crescimento da receita (%)",
                "ebitda_margin_pct": "Margem EBITDA (%)",
                "debt_to_equity": "Dívida / patrimônio",
                "current_ratio": "Liquidez corrente",
                "customer_concentration_pct": "Concentração de clientes (%)",
                "late_payment_pct": "Pagamentos atrasados (%)",
            }
            comparison = filtered_report.set_index("company").loc[
                [company_a, company_b], list(compare_columns)
            ].rename(columns=compare_columns).T
            st.dataframe(comparison.round(2), use_container_width=True)
            st.caption(
                "Indicadores diferentes exigem interpretações diferentes: "
                "crescimento e liquidez não são equivalentes a dívida e atrasos."
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

    history = store.company_history(selected_company)
    if not history.empty:
        with st.expander("Historical snapshots"):
            st.dataframe(history, use_container_width=True, hide_index=True)
            st.caption("Attention score by analysis run")
            st.line_chart(history_chart_data(history))

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
