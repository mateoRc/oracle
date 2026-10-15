# Oracle

The Python/FastAPI question-answering service used by Vaultsh. It answers
questions about Mateo and the Backend Lab project using retrieval over the
shared Markdown content and a hosted language model.

Oracle is read-only: it has no tools, no write mounts, and never changes
anything. It grounds answers in `content/` and returns the source paths it used.
Vaultsh exposes it to users as the read-only `invoke <question>` (lore voice)
and `ask <question>` (plain) commands.
Answers carry a brief, Delphi-inspired voice while staying strictly grounded in
the shared content.

Backend Lab owns its architecture, command, and event documentation.

## Develop

Run the integrated stack:

```sh
cd ../lab
docker compose up --build
```

For direct API development, run the application directly and set the
configuration below, then:

```sh
python -m pytest
uvicorn app.main:app --host 0.0.0.0 --port 8080
```

## Configuration

- `ORACLE_CONTENT_ROOT`: Markdown root; default `/app/content`
- `ORACLE_AUTH_TOKEN`: required bearer token for `POST /ask`
- `ORACLE_PROVIDER`: `openrouter` (default), `groq`, or `mock`
- `ORACLE_MODEL`: model id; defaults to `google/gemma-4-26b-a4b-it:free`
  (openrouter) or `openai/gpt-oss-20b` (groq)
- `ORACLE_MODELS`: OpenRouter-only ordered rotation list, comma-separated (max
  three, OpenRouter's limit); when set it overrides `ORACLE_MODEL` and
  OpenRouter rotates through it as models are rate-limited
- `GROQ_API_KEY`: required when the provider is `groq`
- `GROQ_BASE_URL`: default `https://api.groq.com/openai/v1`
- `OPENROUTER_API_KEY`: required when the provider is `openrouter`
- `OPENROUTER_BASE_URL`: default `https://openrouter.ai/api/v1`
- `ORACLE_API_KEY` / `ORACLE_BASE_URL`: provider-neutral fallbacks used when the
  provider-specific variable above is unset
- `ORACLE_MAX_ANSWER_TOKENS`: default `400`
- `ORACLE_REQUEST_TIMEOUT_SECONDS`: default `25`
- `ORACLE_MAX_CONCURRENCY`: default `4`
- `ORACLE_DAILY_BUDGET`: max upstream questions per UTC day; default `500`
- `ORACLE_CACHE_SIZE`: cached answers; default `128`

Free model ids rotate over time, so pin `ORACLE_MODEL` per deployment. Groq is
the recommended free provider: its free tier allows 1000 requests/day, against
OpenRouter's 50/day without purchased credits.

Set `ORACLE_PROVIDER=mock` to exercise Vaultsh's `ask` command offline without a
provider key. Answers are then deterministic and still cite the matched content
paths.

## Endpoints

- `POST /invoke` `{"question": "..."}` → `{"answer": "...", "sources": ["/cv/about.md", ...]}`
- `POST /ask` `{"question": "..."}` → the same shape, answered plainly
- `GET /healthz` → `ok` (unauthenticated inside the Compose network)
- `GET /status` → `{"status": "ok", "uptime_seconds": 0}`

`invoke` answers in the Oracle's lore voice; `ask` sends no system prompt and
answers plainly. Both require `Authorization: Bearer <ORACLE_AUTH_TOKEN>` and
ground the answer in the same retrieved content. Because `ask` omits the system
prompt, it carries no persona or refusal rules; it still only receives retrieved
public content. When the provider is unavailable or the daily budget is
exhausted, Oracle returns `503` so Vaultsh can degrade to `invoke unavailable`
or `ask unavailable`.

## Test

```sh
docker build --target test .
```
