from typer.testing import CliRunner

from docling.cli.main import app

runner = CliRunner()


def test_cli_help():
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0


def test_cli_version():
    result = runner.invoke(app, ["--version"])
    assert result.exit_code == 0


def test_cli_convert():
    result = runner.invoke(app, ["./tests/data/2305.03393v1-pg9.pdf"])
    assert result.exit_code == 0
