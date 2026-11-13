from pathlib import Path

from streamlit.testing.v1 import AppTest

SCRIPT = Path(__file__).parents[1] / "src" / "swiss_company_intel" / "dashboard.py"


def test_dashboard_loads_and_filters_in_streamlit():
    app = AppTest.from_file(str(SCRIPT)).run(timeout=30)
    assert not app.exception
    assert app.title[0].value == "Swiss Company Intelligence 🇨🇭"
    search = next(item for item in app.text_input if item.label == "Search company name")
    search.set_value("this-company-does-not-exist-xyz").run(timeout=30)
    assert not app.exception
    assert any("No companies match" in item.value for item in app.warning)


def test_saved_runs_are_isolated_between_browser_sessions():
    first = AppTest.from_file(str(SCRIPT)).run(timeout=30)
    save = next(item for item in first.button if item.label == "Save analysis snapshot")
    save.click().run(timeout=30)
    assert not first.exception
    assert any("Saved analysis run #1" in item.value for item in first.success)
    assert any(item.label == "Browse saved analysis runs" for item in first.expander)

    second = AppTest.from_file(str(SCRIPT)).run(timeout=30)
    assert not second.exception
    assert not any(item.label == "Browse saved analysis runs" for item in second.expander)

    first.run(timeout=30)
    assert not first.exception
    assert any(item.label == "Browse saved analysis runs" for item in first.expander)


def test_dashboard_navigation_tabs_and_exports_are_visible():
    app = AppTest.from_file(str(SCRIPT)).run(timeout=30)
    assert not app.exception
    labels = [tab.label for tab in app.tabs]
    assert labels == [
        "📊 Visão geral", "🏢 Empresas", "🧪 Simulador",
        "🗺️ Regiões", "📄 Relatórios", "📚 Fontes e metodologia",
    ]
    downloads = [item.label for item in app.get("button") if "Baixar relatório" in item.label]
    assert downloads or any(
        "Baixar relatório" in str(item) for item in app.get("button")
    )
