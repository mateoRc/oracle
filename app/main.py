import time

from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.responses import PlainTextResponse

from app.auth import require_service_token
from app.models import AskRequest, AskResponse
from app.provider import ProviderError
from app.service import Assistant, BudgetExceeded

app = FastAPI(title="Oracle")
assistant = Assistant.from_environment()
STARTED_AT = time.monotonic()


@app.get("/healthz", response_class=PlainTextResponse)
def health() -> str:
    return "ok"


@app.get("/status")
def service_status() -> dict[str, int | str]:
    return {
        "status": "ok",
        "uptime_seconds": int(time.monotonic() - STARTED_AT),
    }


@app.post("/invoke", dependencies=[Depends(require_service_token)])
def invoke(request: AskRequest) -> AskResponse:
    """Answer in the Oracle's lore voice."""
    return _answer(request.question, lore=True)


@app.post("/ask", dependencies=[Depends(require_service_token)])
def ask(request: AskRequest) -> AskResponse:
    """Answer plainly, without the lore system prompt."""
    return _answer(request.question, lore=False)


def _answer(question: str, *, lore: bool) -> AskResponse:
    try:
        answer, sources = assistant.answer(question, lore=lore)
    except BudgetExceeded as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(error),
        ) from error
    except ProviderError as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="assistant is unavailable",
        ) from error
    return AskResponse(answer=answer, sources=list(sources))
