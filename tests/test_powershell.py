import tempfile
from pathlib import Path
from electorn.execution.powershell import PowerShellExecutionEngine
from electorn.workspace.permissions import PermissionManager


def test_powershell_detection_and_execution():
    with tempfile.TemporaryDirectory() as tmp_dir:
        ps = PowerShellExecutionEngine(workspace_dir=tmp_dir)
        assert ps.executable.lower().endswith((".exe", "powershell", "pwsh"))
        assert ps.powershell_version != ""

        # Run safe expression
        res = ps.run_command("Write-Output 'Electorn PowerShell Engine Test'")
        assert res.returncode == 0
        assert "Electorn PowerShell Engine Test" in res.stdout
        assert res.is_success is True


def test_powershell_file_and_directory_creation():
    with tempfile.TemporaryDirectory() as tmp_dir:
        ps = PowerShellExecutionEngine(workspace_dir=tmp_dir)
        
        # Test creating directory via PowerShell
        res_mkdir = ps.run_command("New-Item -ItemType Directory -Path 'src/nested' -Force")
        assert res_mkdir.returncode == 0
        assert (Path(tmp_dir) / "src" / "nested").is_dir()

        # Test writing file via PowerShell
        res_file = ps.run_command("Set-Content -Path 'src/nested/test.txt' -Value 'Hello PowerShell'")
        assert res_file.returncode == 0
        test_file = Path(tmp_dir) / "src" / "nested" / "test.txt"
        assert test_file.is_file()
        assert test_file.read_text(encoding="utf-8").strip() == "Hello PowerShell"


def test_powershell_background_server_and_stop():
    with tempfile.TemporaryDirectory() as tmp_dir:
        ps = PowerShellExecutionEngine(workspace_dir=tmp_dir)

        # Start a local python http server in background on port 8765
        proc = ps.start_background_server("python -m http.server 8765", name="test-http-server")
        try:
            assert proc.pid > 0

            running_procs = ps.list_active_processes()
            assert any(p.pid == proc.pid for p in running_procs)
        finally:
            # Stop process safely
            stopped = ps.stop_all_processes()
            assert proc.pid in stopped
