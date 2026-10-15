import re
from dataclasses import dataclass
from pathlib import Path

CONTENT_SUFFIXES = (".md", ".markdown", ".txt")
_DEFAULT_PATHS = (
    "/cv/about.md",
    "/docs/projects/overview.md",
    "/cv/skills.md",
    "/cv/experience.md",
)
_TERM = re.compile(r"[a-z0-9]{3,}")
_STOPWORDS = frozenset(
    {
        "the", "and", "for", "are", "was", "were", "what", "which", "who",
        "whom", "how", "why", "when", "where", "does", "did", "doing", "done",
        "can", "could", "would", "should", "have", "has", "had", "you", "your",
        "yours", "with", "about", "from", "this", "that", "these", "those",
        "them", "they", "his", "her", "hers", "its", "our", "ours", "tell",
        "give", "show", "please",
    }
)

# A message made up only of these carries no question, so it is small talk:
# answer it conversationally and ground nothing.
_PLEASANTRIES = frozenset(
    {
        "hi", "hii", "hey", "heya", "hello", "helo", "yo", "howdy", "hiya",
        "greetings", "sup", "morning", "afternoon", "evening", "good", "day",
        "thanks", "thank", "thx", "ty", "cheers", "please", "ok", "okay",
        "cool", "nice", "great", "bye", "goodbye", "cya", "there", "you", "u",
        "how", "are", "doing", "going", "up", "friend", "oracle",
    }
)
_WORD = re.compile(r"[a-z0-9']+")


@dataclass(frozen=True)
class Document:
    path: str
    text: str


class ContentIndex:
    """An in-memory, read-only view of the shared Markdown content."""

    def __init__(self, documents: tuple[Document, ...]) -> None:
        self._documents = documents

    @classmethod
    def from_directory(cls, root: Path) -> "ContentIndex":
        documents: list[Document] = []
        if root.is_dir():
            for file in sorted(root.rglob("*")):
                if not file.is_file() or file.suffix.lower() not in CONTENT_SUFFIXES:
                    continue
                try:
                    text = file.read_text(encoding="utf-8")
                except (OSError, UnicodeDecodeError):
                    continue
                documents.append(
                    Document("/" + file.relative_to(root).as_posix(), text)
                )
        return cls(tuple(documents))

    @property
    def documents(self) -> tuple[Document, ...]:
        return self._documents

    @property
    def document_count(self) -> int:
        return len(self._documents)

    def retrieve(
        self,
        question: str,
        max_files: int,
        max_lines: int,
    ) -> list[tuple[str, str]]:
        terms = _terms(question)
        matches: list[tuple[int, Document, list[str]]] = []
        if terms:
            for document in self._documents:
                lines = [
                    line.strip()
                    for line in document.text.splitlines()
                    if any(term in line.lower() for term in terms)
                ]
                if lines:
                    score = sum(
                        line.lower().count(term) for line in lines for term in terms
                    )
                    matches.append((score, document, lines))

        matches.sort(key=lambda item: (-item[0], item[1].path))
        if matches:
            return [
                (document.path, "\n".join(lines[:max_lines]))
                for _, document, lines in matches[:max_files]
            ]
        return self._default(max_files, max_lines)

    def _default(self, max_files: int, max_lines: int) -> list[tuple[str, str]]:
        by_path = {document.path: document for document in self._documents}
        passages: list[tuple[str, str]] = []
        for path in _DEFAULT_PATHS:
            document = by_path.get(path)
            if document is None:
                continue
            passages.append(_excerpt(document, max_lines))
            if len(passages) >= max_files:
                return passages
        if passages:
            return passages
        return [
            _excerpt(document, max_lines)
            for document in self._documents[:max_files]
        ]


def _excerpt(document: Document, max_lines: int) -> tuple[str, str]:
    return document.path, "\n".join(document.text.splitlines()[:max_lines])


def _terms(question: str) -> list[str]:
    seen: list[str] = []
    for term in _TERM.findall(question.lower()):
        if term not in _STOPWORDS and term not in seen:
            seen.append(term)
    return seen


def is_small_talk(question: str) -> bool:
    """True when the message is only a greeting, thanks, or pleasantry."""
    words = _WORD.findall(question.lower())
    return bool(words) and all(word in _PLEASANTRIES for word in words)
