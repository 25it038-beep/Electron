import unittest.mock as mock
from electorn.runtime.web_search import SearchResult, WebSearchEngine


def test_web_search_format_table_and_context():
    engine = WebSearchEngine()
    results = [
        SearchResult(
            title="FastAPI Documentation",
            url="https://fastapi.tiangolo.com",
            snippet="FastAPI framework, high performance, easy to learn, fast to code.",
        ),
        SearchResult(
            title="Python Official Website",
            url="https://python.org",
            snippet="Python is a programming language that lets you work quickly.",
        ),
    ]

    # Test context prompt generation
    context = engine.format_context_prompt("python web frameworks", results)
    assert "[WEB SEARCH CONTEXT for: 'python web frameworks']" in context
    assert "FastAPI Documentation" in context
    assert "https://fastapi.tiangolo.com" in context
    assert "[END WEB SEARCH CONTEXT]" in context

    # Test Rich table generation
    table = engine.format_table("python web frameworks", results)
    assert table is not None
    assert table.title is not None
    assert "python web frameworks" in table.title


def test_web_search_empty_query():
    engine = WebSearchEngine()
    assert engine.search("") == []
    assert engine.search("   ") == []


def test_web_search_instant_parser():
    engine = WebSearchEngine()
    mock_data = {
        "Heading": "Python (programming language)",
        "AbstractText": "Python is a high-level, general-purpose programming language.",
        "AbstractURL": "https://en.wikipedia.org/wiki/Python_(programming_language)",
        "RelatedTopics": [
            {
                "Text": "Django (web framework) - Python web framework",
                "FirstURL": "https://en.wikipedia.org/wiki/Django_(web_framework)",
            }
        ],
    }

    mock_resp = mock.MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = mock_data

    with mock.patch("httpx.Client.get", return_value=mock_resp):
        results = engine._search_duckduckgo_instant("python", max_results=2)
        assert len(results) == 2
        assert "Python" in results[0].title
        assert "high-level" in results[0].snippet
        assert results[0].url.startswith("https://")
