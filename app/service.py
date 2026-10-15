import re
import threading
from collections import OrderedDict
from datetime import UTC, datetime

from app.config import Config
from app.content import ContentIndex, is_small_talk
from app.provider import SYSTEM_PROMPT, Passage, Provider, build_provider


class BudgetExceeded(Exception):
    """Raised when the daily upstream question budget is exhausted."""


class Assistant:
    """Coordinates retrieval, the provider call, caching, and abuse limits."""

    def __init__(
        self,
        index: ContentIndex,
        provider: Provider,
        config: Config,
    ) -> None:
        self._index = index
        self._provider = provider
        self._config = config
        self._semaphore = threading.BoundedSemaphore(config.max_concurrency)
        self._lock = threading.Lock()
        self._cache: OrderedDict[str, tuple[str, tuple[str, ...]]] = OrderedDict()
        self._budget_day = datetime.now(UTC).date()
        self._budget_used = 0

    @classmethod
    def from_environment(cls) -> "Assistant":
        config = Config.from_environment()
        return cls(
            ContentIndex.from_directory(config.content_root),
            build_provider(config),
            config,
        )

    @property
    def provider_name(self) -> str:
        return self._provider.name

    @property
    def document_count(self) -> int:
        return self._index.document_count

    def answer(
        self,
        question: str,
        *,
        lore: bool = True,
    ) -> tuple[str, tuple[str, ...]]:
        if re.fullmatch(r"\s*who\s+am\s+i\s*[?!.\s]*", question, re.IGNORECASE):
            if lore:
                return (
                    "Seeker, I cannot identify you from this question. You are visiting Mateo's Backend Lab portfolio.",
                    (),
                )
            return (
                "I cannot identify you from this question. You are visiting Mateo's Backend Lab portfolio.",
                (),
            )
        mode = "lore" if lore else "plain"
        key = f"{mode}:{' '.join(question.lower().split())}"
        with self._lock:
            cached = self._cache.get(key)
            if cached is not None:
                self._cache.move_to_end(key)
                return cached

        self._reserve_budget()
        passages = (
            []
            if is_small_talk(question)
            else self._index.retrieve(
                question,
                self._config.retrieval_files,
                self._config.retrieval_lines,
            )
        )
        with self._semaphore:
            answer = self._provider.answer(
                question,
                tuple(Passage(path, text) for path, text in passages),
                SYSTEM_PROMPT if lore else None,
            )
        answer = answer.strip()
        sources = tuple(path for path, _ in passages)

        with self._lock:
            self._cache[key] = (answer, sources)
            while len(self._cache) > self._config.cache_size:
                self._cache.popitem(last=False)
        return answer, sources

    def _reserve_budget(self) -> None:
        today = datetime.now(UTC).date()
        with self._lock:
            if today != self._budget_day:
                self._budget_day = today
                self._budget_used = 0
            if self._budget_used >= self._config.daily_budget:
                raise BudgetExceeded("daily question budget reached")
            self._budget_used += 1
