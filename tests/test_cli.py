from typer.testing import CliRunner
from cloak.__main__ import main
from cloak.cli import app

runner = CliRunner()

def test_help():
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "PII scrubber" in result.stdout
