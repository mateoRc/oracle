from pathlib import Path

from app.content import ContentIndex

FIXTURES = Path(__file__).parent / "fixtures" / "content"


def test_index_loads_markdown_documents() -> None:
    index = ContentIndex.from_directory(FIXTURES)
    paths = {document.path for document in index.documents}

    assert "/cv/about.md" in paths
    assert "/docs/projects/overview.md" in paths
    assert index.document_count >= 4


def test_retrieve_returns_matching_documents() -> None:
    index = ContentIndex.from_directory(FIXTURES)

    passages = index.retrieve("Which languages does Mateo use?", 4, 6)

    assert passages
    assert any("skills" in path for path, _ in passages)


def test_retrieve_falls_back_to_defaults_without_terms() -> None:
    index = ContentIndex.from_directory(FIXTURES)

    passages = index.retrieve("hello", 4, 2)

    assert passages
    assert passages[0][0] == "/cv/about.md"


def test_missing_directory_yields_empty_index() -> None:
    index = ContentIndex.from_directory(FIXTURES / "does-not-exist")

    assert index.document_count == 0
    assert index.retrieve("anything", 4, 6) == []
