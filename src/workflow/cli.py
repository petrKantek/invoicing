"""Typer CLI for invoice batch initialization and processing."""

from datetime import date
from pathlib import Path

import typer

from src.parsers.base_parser import PDFParseError
from src.workflow.batch_processor import InvoiceBatchProcessor

app = typer.Typer(help="Initialize invoice folders and process vendor batches.")


def _parse_iso_date(value: str, parameter_name: str) -> date:
    """Parse a YYYY-MM-DD date value for CLI commands."""
    try:
        return date.fromisoformat(value)
    except ValueError as error:
        raise typer.BadParameter(
            f"{parameter_name} must use YYYY-MM-DD format"
        ) from error


@app.command("init")
def init_batch(
    start_date: str = typer.Argument(..., help="Start date in YYYY-MM-DD format."),
    end_date: str = typer.Argument(..., help="End date in YYYY-MM-DD format."),
    destination_root: Path = typer.Option(
        Path("data/batches"),
        "--destination-root",
        "-d",
        help="Root directory where the batch folder will be created.",
    ),
) -> None:
    """Create the vendor folder structure for a date interval."""
    processor = InvoiceBatchProcessor()
    parsed_start_date = _parse_iso_date(start_date, "start_date")
    parsed_end_date = _parse_iso_date(end_date, "end_date")

    try:
        batch_dir = processor.initialize_batch_directories(
            parsed_start_date,
            parsed_end_date,
            destination_root,
        )
    except ValueError as error:
        raise typer.BadParameter(str(error)) from error

    typer.echo(f"Created batch directory: {batch_dir}")
    typer.echo(f"Instructions: {(batch_dir / 'README.txt')}")


@app.command("process")
def process_batch(
    start_date: str = typer.Argument(..., help="Start date in YYYY-MM-DD format."),
    end_date: str = typer.Argument(..., help="End date in YYYY-MM-DD format."),
    starting_invoice_id: int = typer.Option(
        ...,
        "--starting-invoice-id",
        help="First accounting invoice id to append as _<id> and increment by 1.",
    ),
    destination_root: Path = typer.Option(
        Path("data/batches"),
        "--destination-root",
        "-d",
        help="Root directory containing the batch folder.",
    ),
) -> None:
    """Parse vendor folders, export XML, and write review reports."""
    processor = InvoiceBatchProcessor()
    parsed_start_date = _parse_iso_date(start_date, "start_date")
    parsed_end_date = _parse_iso_date(end_date, "end_date")
    batch_dir = processor.build_batch_dir(
        parsed_start_date,
        parsed_end_date,
        destination_root,
    )

    try:
        result = processor.process_batch(batch_dir, starting_invoice_id)
    except PDFParseError as error:
        typer.echo(str(error), err=True)
        raise typer.Exit(code=1) from error

    typer.echo(f"Processed batch directory: {result.batch_dir}")
    typer.echo(f"Invoice report: {result.report_csv}")
    typer.echo(f"Summary report: {result.summary_txt}")
    if result.xml_outputs:
        typer.echo("XML outputs:")
        for xml_output in result.xml_outputs:
            typer.echo(f"- {xml_output}")


def main() -> None:
    """Run the Typer application."""
    app()


if __name__ == "__main__":
    main()