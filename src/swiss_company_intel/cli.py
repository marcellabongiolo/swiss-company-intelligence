from __future__ import annotations

from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

from .analyzer import CompanyAnalyzer
from .io import load_companies

app = typer.Typer(
    help="Explainable screening and benchmarking of Swiss companies.",
    no_args_is_help=True,
)
console = Console()


@app.callback()
def main() -> None:
    """Swiss Company Intelligence command-line interface."""


@app.command()
def analyze(
    input_file: Path = typer.Argument(..., help="CSV file containing company metrics."),
    output: Path = typer.Option(
        Path("reports/company_attention_report.csv"),
        "--output",
        "-o",
        help="Destination CSV report.",
    ),
    top: int = typer.Option(10, min=1, help="Number of rows shown in the terminal."),
) -> None:
    """Analyze a CSV portfolio and rank companies by analyst-attention score."""
    try:
        df = load_companies(input_file)
        analyzer = CompanyAnalyzer()
        analyzed = analyzer.analyze(df)
        report = analyzer.report_columns(analyzed)

        output.parent.mkdir(parents=True, exist_ok=True)
        report.to_csv(output, index=False)

        table = Table(title="Swiss Company Intelligence — Attention Ranking")
        table.add_column("Rank", justify="right")
        table.add_column("Company")
        table.add_column("Canton")
        table.add_column("Sector")
        table.add_column("Score", justify="right")
        table.add_column("Band")
        table.add_column("Main signals")

        for idx, row in report.head(top).iterrows():
            table.add_row(
                str(idx + 1),
                str(row["company"]),
                str(row["canton"]),
                str(row["sector"]),
                f"{row['attention_score']:.1f}",
                str(row["priority_band"]),
                str(row["reasons"]),
            )

        console.print(table)
        console.print(f"\n[green]Report written to:[/green] {output}")
        console.print(
            "[dim]Synthetic demo data and heuristic scores are for software demonstration only.[/dim]"
        )
    except Exception as exc:
        console.print(f"[red]Error:[/red] {exc}")
        raise typer.Exit(code=1) from exc


if __name__ == "__main__":
    app()
