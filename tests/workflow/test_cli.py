from pathlib import Path

from typer.testing import CliRunner

from src.workflow.cli import app

runner = CliRunner()


def test_init_command_creates_vendor_structure(tmp_path: Path) -> None:
    result = runner.invoke(
        app,
        [
            "init",
            "2026-06-01",
            "2026-06-30",
            "--destination-root",
            str(tmp_path),
        ],
    )

    batch_dir = tmp_path / "2026-06-01_2026-06-30"

    assert result.exit_code == 0
    assert batch_dir.exists()
    assert (batch_dir / "README.txt").exists()
    assert (batch_dir / "phoenix" / "invoices").exists()
    assert (batch_dir / "phoenix" / "invoices" / "prusanky").exists()
    assert (batch_dir / "phoenix" / "invoices" / "bojanovice").exists()
    assert (batch_dir / "phoenix" / "output").exists()
    assert (batch_dir / "phoenix" / "output" / "prusanky").exists()
    assert (batch_dir / "phoenix" / "output" / "bojanovice").exists()
    assert (batch_dir / "alliance" / "invoices").exists()
    assert (batch_dir / "noviko" / "output").exists()


def test_process_command_generates_xml_and_reports(tmp_path: Path) -> None:
    init_result = runner.invoke(
        app,
        [
            "init",
            "2026-06-01",
            "2026-06-30",
            "--destination-root",
            str(tmp_path),
        ],
    )
    assert init_result.exit_code == 0

    batch_dir = tmp_path / "2026-06-01_2026-06-30"
    fixture_pdf = Path("tests/fixtures/pdfs/phoenix/f7021241452.pdf")
    first_target_pdf = batch_dir / "phoenix" / "invoices" / fixture_pdf.name
    second_target_pdf = batch_dir / "phoenix" / "invoices" / "copy_f7021241452.pdf"
    first_target_pdf.write_bytes(fixture_pdf.read_bytes())
    second_target_pdf.write_bytes(fixture_pdf.read_bytes())

    process_result = runner.invoke(
        app,
        [
            "process",
            "2026-06-01",
            "2026-06-30",
            "--starting-invoice-id",
            "226100",
            "--destination-root",
            str(tmp_path),
        ],
    )

    aggregated_xml_output = batch_dir / "phoenix" / "output" / "phoenix_2026-06-01_2026-06-30.xml"
    first_processed_pdf = batch_dir / "phoenix" / "output" / "copy_f7021241452_226100.pdf"
    second_processed_pdf = batch_dir / "phoenix" / "output" / "f7021241452_226101.pdf"
    report_csv = batch_dir / "extraction_report.csv"
    summary_txt = batch_dir / "processing_summary.txt"

    assert process_result.exit_code == 0
    assert aggregated_xml_output.exists()
    assert first_processed_pdf.exists()
    assert second_processed_pdf.exists()
    assert report_csv.exists()
    assert summary_txt.exists()
    xml_content = aggregated_xml_output.read_text(encoding="utf-8")
    assert xml_content.count("<FaktPrij>") == 2
    assert "<PrijatDokl>7021241452</PrijatDokl>" in xml_content
    assert "<VarSymbol>7021241452</VarSymbol>" in xml_content
    report_content = report_csv.read_text(encoding="utf-8")
    assert "f7021241452.pdf" in report_content
    assert "phoenix" in report_content
    assert "copy_f7021241452_226100.pdf" in report_content
    assert "f7021241452_226101.pdf" in report_content
    assert ",226100," in report_content
    assert ",226101," in report_content
    summary_content = summary_txt.read_text(encoding="utf-8")
    assert "processed" in summary_content
    assert "Vendor: phoenix" in summary_content


def test_process_command_uses_shared_invoice_suffix_across_vendors(tmp_path: Path) -> None:
    init_result = runner.invoke(
        app,
        [
            "init",
            "2026-06-01",
            "2026-06-30",
            "--destination-root",
            str(tmp_path),
        ],
    )
    assert init_result.exit_code == 0

    batch_dir = tmp_path / "2026-06-01_2026-06-30"
    alliance_pdf = Path("data/alliance/alliance.pdf")
    phoenix_pdf = Path("tests/fixtures/pdfs/phoenix/f7021241452.pdf")
    (batch_dir / "alliance" / "invoices" / alliance_pdf.name).write_bytes(alliance_pdf.read_bytes())
    (batch_dir / "phoenix" / "invoices" / phoenix_pdf.name).write_bytes(phoenix_pdf.read_bytes())
    (batch_dir / "phoenix" / "invoices" / "copy_f7021241452.pdf").write_bytes(phoenix_pdf.read_bytes())

    process_result = runner.invoke(
        app,
        [
            "process",
            "2026-06-01",
            "2026-06-30",
            "--starting-invoice-id",
            "226100",
            "--destination-root",
            str(tmp_path),
        ],
    )

    assert process_result.exit_code == 0

    alliance_outputs = sorted((batch_dir / "alliance" / "output").glob("*.pdf"))
    phoenix_outputs = sorted((batch_dir / "phoenix" / "output").glob("*.pdf"))

    assert [path.name for path in alliance_outputs] == ["alliance_226100.pdf"]
    assert [path.name for path in phoenix_outputs] == [
        "copy_f7021241452_226101.pdf",
        "f7021241452_226102.pdf",
    ]


def test_process_command_preserves_phoenix_input_subfolder_order(tmp_path: Path) -> None:
    init_result = runner.invoke(
        app,
        [
            "init",
            "2026-06-01",
            "2026-06-30",
            "--destination-root",
            str(tmp_path),
        ],
    )
    assert init_result.exit_code == 0

    batch_dir = tmp_path / "2026-06-01_2026-06-30"
    phoenix_prusanky_pdf = Path("tests/fixtures/pdfs/phoenix/f7021241452.pdf")
    phoenix_bojanovice_pdf = Path("tests/fixtures/pdfs/phoenix/2260009385-226180.pdf")

    (batch_dir / "phoenix" / "invoices" / "prusanky" / phoenix_prusanky_pdf.name).write_bytes(
        phoenix_prusanky_pdf.read_bytes()
    )
    (batch_dir / "phoenix" / "invoices" / "bojanovice" / phoenix_bojanovice_pdf.name).write_bytes(
        phoenix_bojanovice_pdf.read_bytes()
    )

    process_result = runner.invoke(
        app,
        [
            "process",
            "2026-06-01",
            "2026-06-30",
            "--starting-invoice-id",
            "226100",
            "--destination-root",
            str(tmp_path),
        ],
    )

    assert process_result.exit_code == 0

    prusanky_outputs = sorted((batch_dir / "phoenix" / "output" / "prusanky").glob("*.pdf"))
    bojanovice_outputs = sorted((batch_dir / "phoenix" / "output" / "bojanovice").glob("*.pdf"))

    assert [path.name for path in bojanovice_outputs] == ["2260009385-226180_226100.pdf"]
    assert [path.name for path in prusanky_outputs] == ["f7021241452_226101.pdf"]

    report_content = (batch_dir / "extraction_report.csv").read_text(encoding="utf-8")
    assert "2260009385-226180.pdf" in report_content
    assert "f7021241452.pdf" in report_content
    assert ",226100," in report_content
    assert ",226101," in report_content


def test_process_command_fails_for_missing_batch_dir(tmp_path: Path) -> None:
    result = runner.invoke(
        app,
        [
            "process",
            "2026-06-01",
            "2026-06-30",
            "--starting-invoice-id",
            "226100",
            "--destination-root",
            str(tmp_path),
        ],
    )

    assert result.exit_code == 1
    assert "Batch directory not found" in result.output