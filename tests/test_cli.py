from typer.testing import CliRunner
from electorn.cli import app

runner = CliRunner()


def test_cli_help():
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "Electorn AI" in result.output
    assert "doctor" in result.output
    assert "models" in result.output


def test_cli_doctor():
    result = runner.invoke(app, ["doctor"])
    assert result.exit_code == 0
    assert "System & Developer Environment Audit" in result.output
    assert "Operating System" in result.output


def test_cli_init_and_run_mock():
    with runner.isolated_filesystem():
        # Init
        init_res = runner.invoke(app, ["init"])
        assert init_res.exit_code == 0
        assert "Created Electorn configuration" in init_res.output

        # Run mock via explicit 'run' command
        run_res = runner.invoke(app, ["run", "Build a minimal calculator", "--mock", "-y"])
        assert run_res.exit_code == 0
        assert "Autonomous Application Build Finished" in run_res.output

        # Run mock via direct prompt (electorn "<prompt>")
        direct_res = runner.invoke(app, ["Build a second tool", "--mock", "-y"])
        assert direct_res.exit_code == 0
        assert "Autonomous Application Build Finished" in direct_res.output


def test_cli_studio():
    result = runner.invoke(app, ["studio"])
    assert result.exit_code == 0
    assert "HS AI Solutions" in result.output
    assert "https://hs-ai-studio.onrender.com/" in result.output
    assert "Pendulum" in result.output
    assert "Lumina" in result.output
    assert "Ledger" in result.output


def test_cli_new_commands():
    # Test version
    ver_res = runner.invoke(app, ["version"])
    assert ver_res.exit_code == 0
    assert "Electorn AI" in ver_res.output

    with runner.isolated_filesystem():
        # Test config
        cfg_res = runner.invoke(app, ["config"])
        assert cfg_res.exit_code == 0
        assert "Electorn Configuration" in cfg_res.output

        # Test mode
        mode_res = runner.invoke(app, ["mode", "local"])
        assert mode_res.exit_code == 0
        assert "LOCAL" in mode_res.output

        # Test status
        status_res = runner.invoke(app, ["status"])
        assert status_res.exit_code == 0
        assert "Workspace Status" in status_res.output

        # Test checkpoint
        cp_res = runner.invoke(app, ["checkpoint", "test cp"])
        assert cp_res.exit_code == 0
        assert "Created snapshot checkpoint" in cp_res.output

        # Test analyze
        an_res = runner.invoke(app, ["analyze", "."])
        assert an_res.exit_code == 0
        assert "Codebase Intelligence" in an_res.output


