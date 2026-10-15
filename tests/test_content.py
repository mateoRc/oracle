from pathlib import Path

from app.content import ContentIndex, Document, is_small_talk

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


def test_retrieve_prioritizes_subject_over_common_question_words() -> None:
    documents = tuple(
        Document(f"/docs/page-{number}.md", "Mateo uses the project tools. " * 10)
        for number in range(5)
    ) + (Document("/cv/skills.md", "Languages: Python, Java, Go."),)
    index = ContentIndex(documents)

    passages = index.retrieve("Which languages does Mateo use?", 4, 6)

    assert passages[0][0] == "/cv/skills.md"


def test_generic_project_question_includes_overview_summary() -> None:
    documents = (
        Document("/docs/content.md", "Project project project project."),
        Document(
            "/docs/projects/overview.md",
            "Backend Lab is a read-only portfolio terminal.\nProjects live here.",
        ),
    )

    passages = ContentIndex(documents).retrieve(
        "explain this project, where am i?", 2, 2
    )

    assert passages[0] == (
        "/docs/projects/overview.md",
        "Backend Lab is a read-only portfolio terminal.\nProjects live here.",
    )


def test_location_question_does_not_retrieve_mateos_bio() -> None:
    index = ContentIndex.from_directory(FIXTURES)

    assert index.retrieve("where am I?", 4, 6) == []


def test_retrieve_falls_back_to_defaults_without_terms() -> None:
    index = ContentIndex.from_directory(FIXTURES)

    passages = index.retrieve("hello", 4, 2)

    assert passages
    assert passages[0][0] == "/cv/about.md"


def test_missing_directory_yields_empty_index() -> None:
    index = ContentIndex.from_directory(FIXTURES / "does-not-exist")

    assert index.document_count == 0
    assert index.retrieve("anything", 4, 6) == []


def test_small_talk_recognises_greetings() -> None:
    assert is_small_talk("hello")
    assert is_small_talk("Hi there!")
    assert is_small_talk("thank you")


def test_small_talk_rejects_real_questions() -> None:
    assert not is_small_talk("who is Mateo")
    assert not is_small_talk("hello, what is Vaultsh?")
    assert not is_small_talk("")
