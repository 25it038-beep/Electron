from pathlib import Path
from electorn.workspace.checkpoints import CheckpointManager


def test_checkpoint_lifecycle(tmp_path: Path):
    ws = tmp_path / "project"
    ws.mkdir()
    (ws / "app.py").write_text("print('v1')", encoding="utf-8")

    mgr = CheckpointManager(ws)

    # 1. Create checkpoint
    cid = mgr.create_checkpoint("Initial version")
    assert cid.startswith("cp-")
    assert len(mgr.list_checkpoints()) == 1

    # 2. Modify file
    (ws / "app.py").write_text("print('v2 modified')", encoding="utf-8")
    diff_text = mgr.diff(cid)
    assert "-print('v1')" in diff_text
    assert "+print('v2 modified')" in diff_text

    # 3. Rollback
    success = mgr.rollback(cid)
    assert success is True
    assert (ws / "app.py").read_text(encoding="utf-8") == "print('v1')"

    # 4. Diff after rollback
    assert "No differences" in mgr.diff(cid)
