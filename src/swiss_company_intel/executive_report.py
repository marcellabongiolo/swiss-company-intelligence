"""Printable, self-contained HTML executive report for analyzed companies."""
from __future__ import annotations

from html import escape

import pandas as pd


def executive_report_html(report: pd.DataFrame) -> bytes:
    """Build a printable report without embedding untrusted HTML from CSV uploads."""
    required = {"company", "sector", "canton", "attention_score", "priority_band", "reasons"}
    missing = required.difference(report.columns)
    if missing:
        raise ValueError(f"Missing report columns: {', '.join(sorted(missing))}")
    if report.empty:
        raise ValueError("Cannot export an empty report")

    ordered = report.sort_values("attention_score", ascending=False)
    rows = []
    for _, company in ordered.iterrows():
        cells = [
            company["company"], company["sector"], company["canton"],
            f'{float(company["attention_score"]):.1f}',
            company["priority_band"], company["reasons"],
        ]
        rows.append("<tr>" + "".join(
            f"<td>{escape(str(value), quote=True)}</td>" for value in cells
        ) + "</tr>")
    count = len(ordered)
    avg_score = float(ordered["attention_score"].mean())
    high = int(ordered["priority_band"].isin(["high", "critical"]).sum())
    content = f"""<!doctype html>
<html lang="pt-BR"><head><meta charset="utf-8">
<title>Relatório executivo — Swiss Company Intelligence</title>
<style>
body{{font:15px Arial,sans-serif;color:#172b4d;max-width:1100px;margin:40px auto;padding:0 20px}}
h1{{color:#153e75}}.notice{{background:#f0f6ff;border-left:5px solid #2563eb;padding:15px}}
.summary{{display:flex;gap:18px;margin:24px 0;flex-wrap:wrap}}
.summary div{{background:#f4f7fb;border-radius:10px;padding:18px;min-width:160px}}
strong{{font-size:22px}}table{{border-collapse:collapse;width:100%;font-size:12px}}
th,td{{padding:10px;text-align:left;border-bottom:1px solid #dbe3ed;vertical-align:top}}
th{{background:#e8eff9}}@media print{{body{{margin:0}}.summary{{break-inside:avoid}}}}
</style></head><body>
<h1>🇨🇭 Swiss Company Intelligence</h1>
<h2>Relatório executivo de triagem empresarial</h2>
<p class="notice"><b>Demonstração com dados sintéticos.</b> Os indicadores individuais
não são resultados financeiros reais. A pontuação representa prioridade de
revisão, não risco de falência, rating de crédito ou recomendação de investimento.</p>
<div class="summary">
<div>Empresas<br><strong>{count}</strong></div>
<div>Atenção média<br><strong>{avg_score:.1f}/100</strong></div>
<div>Prioridade alta/crítica<br><strong>{high}</strong></div>
</div>
<h2>Empresas analisadas</h2>
<table><thead><tr><th>Empresa</th><th>Setor</th><th>Cantão</th>
<th>Atenção</th><th>Faixa</th><th>Motivos</th></tr></thead>
<tbody>{''.join(rows)}</tbody></table>
<h2>Metodologia e interpretação</h2>
<p>O modelo combina indicadores financeiros e operacionais com anomalias
estatísticas relativas ao setor. Faixas: 0–25 baixa; acima de 25–50 moderada;
acima de 50–75 alta; acima de 75–100 crítica. Resultados dependem da
amostra e dos pesos selecionados.</p>
<p>Para salvar como PDF, abra este arquivo no navegador e use Imprimir → Salvar como PDF.</p>
</body></html>"""
    return content.encode("utf-8")
