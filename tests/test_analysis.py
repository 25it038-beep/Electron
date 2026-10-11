from pathlib import Path
from electorn.analysis.codebase_analyzer import CodebaseAnalyzer


def test_codebase_analyzer(tmp_path: Path):
    ws = tmp_path / "repo"
    ws.mkdir()
    (ws / "main.py").write_text("@app.get('/api/users')\ndef get_users(): pass\n", encoding="utf-8")
    (ws / "models.py").write_text("class User(Base): pass\n", encoding="utf-8")
    (ws / "package.json").write_text('{"name": "test"}', encoding="utf-8")

    # Add secret leak to test scanner
    (ws / "config.py").write_text("API_KEY = 'sk-12345678901234567890123456789012'\n", encoding="utf-8")

    analyzer = CodebaseAnalyzer(ws)
    summary = analyzer.analyze()

    assert summary.total_files == 4
    assert "Python" in summary.languages
    assert "JSON" in summary.languages
    assert "main.py" in summary.entry_points
    assert len(summary.route_endpoints) == 1
    assert "/api/users" in summary.route_endpoints[0]
    assert len(summary.database_models) == 1
    assert "User" in summary.database_models[0]
    assert len(summary.security_findings) >= 1
    rules = [f.rule for f in summary.security_findings]
    assert "OpenAI API Key" in rules
