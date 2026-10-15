# Oracle

The Python/FastAPI question-answering service used by Vaultsh. It answers
questions about Mateo and the Backend Lab project using retrieval over the
shared Markdown content and a hosted language model.

Oracle is read-only: it has no tools, no write mounts, and never changes
anything. It grounds answers in `content/` and returns the source paths it used.
Vaultsh exposes it to users as the read-only `invoke <question>` command.

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
- `ORACLE_PROVIDER`: `openrouter` (default) or `mock`
- `ORACLE_MODEL`: OpenRouter model id; default `openai/gpt-oss-20b:free`
- `OPENROUTER_API_KEY`: required when the provider is `openrouter`
- `OPENROUTER_BASE_URL`: default `https://openrouter.ai/api/v1`
- `ORACLE_MAX_ANSWER_TOKENS`: default `400`
- `ORACLE_REQUEST_TIMEOUT_SECONDS`: default `25`
- `ORACLE_MAX_CONCURRENCY`: default `4`
- `ORACLE_DAILY_BUDGET`: max upstream questions per UTC day; default `500`
- `ORACLE_CACHE_SIZE`: cached answers; default `128`

Free model ids rotate over time, so pin `ORACLE_MODEL` per deployment.

Set `ORACLE_PROVIDER=mock` to exercise Vaultsh's `ask` command offline without a
provider key. Answers are then deterministic and still cite the matched content
paths.

## Endpoints

- `POST /ask` `{"question": "..."}` → `{"answer": "...", "sources": ["/cv/about.md", ...]}`
- `GET /healthz` → `ok` (unauthenticated inside the Compose network)
- `GET /status` → `{"status": "ok", "uptime_seconds": 0}`

`POST /ask` requires `Authorization: Bearer <ORACLE_AUTH_TOKEN>`. When the
provider is unavailable or the daily budget is exhausted, Oracle returns
`503` so Vaultsh can degrade to `invoke unavailable`.

## Test

```sh
docker build --target test .
```
