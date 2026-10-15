from pydantic import BaseModel, ConfigDict, Field

MAX_QUESTION_CHARS = 500


class AskRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    question: str = Field(min_length=1, max_length=MAX_QUESTION_CHARS)


class AskResponse(BaseModel):
    answer: str
    sources: list[str]
