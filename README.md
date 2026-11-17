# AkadVerse Productivity AI — standalone service

This repository is the independently deployable PIP assistant extracted from
`akadverse/akadverse-productivity-ai`. It preserves the existing Gemini agent,
registered tools, request limits, delegated authentication, and backend callbacks.
It does not require the AkadVerse source checkout at runtime.

AkadVerse remains the application backend: student login, productivity records,
business rules, conversation history, confirmation previews, mutation receipts,
and reconciliation live there. This service has no database credentials.

## Run locally

Python 3.13 is the Docker runtime.

With Node.js 18+ and Python installed, start development with:

```sh
npm run dev
```

The first run creates `.venv` and installs the pinned Python dependencies.
Configure `.env` from `.env.example` before starting. The service reloads on code
changes and listens on `http://127.0.0.1:8000`. Set `PORT` in `.env` or your shell
to change the port; update AkadVerse's `PRODUCTIVITY_AI_SERVICE_URL` to match.
No `npm install` is needed. Optionally set `PYTHON` to an existing Python executable
with the dependencies installed to use that environment instead.

To set up and start manually:

```sh
python3 -m venv .venv
.venv/bin/pip install -r requirements.lock
cp .env.example .env
# Fill in .env with the matching AkadVerse credentials and your provider key.
.venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8000 --no-access-log
```

For local development set AkadVerse's `PRODUCTIVITY_AI_SERVICE_URL` to
`http://127.0.0.1:8000`, and this service's `AKADVERSE_API_BASE_URL` to
`http://localhost:3000` (or the actual Next.js port).

Check liveness with `curl --fail http://127.0.0.1:8000/health`.
The response is `{"status":"ok"}`; it does not test provider credentials or the backend.
The health route can succeed before credentials are configured. Assistant requests
require all required configuration.

## Environment variables

Copy `.env.example` for this service. Set production secrets through your hosting
provider. Never commit `.env` or use `NEXT_PUBLIC_*` for any credential.

| Variable | Location | Purpose |
| --- | --- | --- |
| `GEMINI_API_KEY` | Python, required | Gemini provider key. |
| `GEMINI_MODEL` | Python, optional | Preserved source default: `gemini-3.5-flash-lite`. Verify availability for your Google project; no provider availability is implied. |
| `AKADVERSE_API_BASE_URL` | Python, required | Canonical AkadVerse origin, without a path. HTTPS in production; HTTP allowed for localhost/127.0.0.1. |
| `PRODUCTIVITY_AI_SERVICE_TOKEN` | Both, required | Identical dedicated secret, at least 32 characters. |
| `PRODUCTIVITY_AI_JWT_PUBLIC_KEY` | Python required; AkadVerse recommended | Matching RS256 public PEM. Escaped `\n` is supported. |
| `PRODUCTIVITY_AI_JWT_PRIVATE_KEY` | AkadVerse only, required | RS256 private PEM used to sign delegations. Never put it in Python. |
| `PRODUCTIVITY_AI_JWT_KEY_ID` | Both | Must match; default `productivity-v1`. |
| `PRODUCTIVITY_AI_SERVICE_URL` | AkadVerse only, required | Public HTTPS origin of this hosted Python service. |
| `MAX_TOOL_CALLS` | Python, optional | 1–10; default 10 per turn. |
| `TURN_TIMEOUT_SECONDS` | Python, optional | 5–55; default 55. |
| `PORT` | Container, optional | Uvicorn listen port; default 8000. For manual uvicorn use `--port`. |
| `ASSEMBLYAI_API_KEY` | AkadVerse only, optional | Enables existing browser voice transcription. |
| Existing database / NextAuth configuration | AkadVerse only | Retained by the application; not required in Python. |

`docs/akadverse.env.example` contains the companion server settings.
Reuse your existing matching keys/token when connecting to the current AkadVerse
installation. For a fresh installation, `python3 scripts/generate_credentials.py`
creates ignored files under `.credentials/`, without printing secrets. Transfer
those values to each host's secret manager. Replacing an existing credential
requires updating both services together.

## Deploy

Build this repository's Dockerfile as the service root:

```sh
docker build -t akadverse-productivity-ai .
docker run --rm --env-file .env -p 8000:8000 akadverse-productivity-ai
```

The image installs pinned dependencies and runs as a non-root user. It respects
hosting platforms' `PORT`. Configure `/health` as the health check. Supply the
Python variables above and set AkadVerse's `PRODUCTIVITY_AI_SERVICE_URL` to the
resulting HTTPS origin. Both servers must be able to reach each other over HTTPS.
Allow requests lasting at least 65 seconds through your proxy/platform; Python's
turn deadline is 55 seconds and AkadVerse's service request timeout is 65 seconds.

AkadVerse must already expose `/api/productivity/assistant` and
`/api/productivity/assistant/service`, include its assistant persistence migration
`20261115000000_productivity_ai_assistant`, and have a generated Prisma client.
Deploy any unapplied migration through AkadVerse's normal migration workflow.
The exact service callback must pass the application's proxy cookie gate; its own
service-token and JWT checks still apply. The browser uses AkadVerse, so CORS
configuration on Python is unnecessary for this integration.

Keep AkadVerse's existing embedded registry file: its TypeScript schema imports
`akadverse-productivity-ai/app/tools/definitions.json`. Deploying Python separately
does not require deleting that directory. When changing the tool contract, update
both registries together; see [the architecture and extraction audit](docs/architecture.md).

## Verification

```sh
.venv/bin/pip install -r requirements-dev.txt
.venv/bin/python -m pytest -q
```

Tests use mocked providers and HTTP transports. After deployment, sign in to
AkadVerse and open `/studashboard/productivity-layer` → Assistant:

1. Ask for the account timezone and today's date.
2. Create a disposable task and verify it appears after refreshing the workspace.
3. Ask to edit it; inspect the proposal, Cancel, and verify no change. Repeat and Confirm.
4. Ask to delete it and verify confirmation is required.
5. Test a habit, schedule read, and analytics request.
6. Verify another account cannot see the conversation or its records.
7. After an interrupted write, use Recheck outcome before repeating the request.

These steps require a configured live backend and provider; mock tests and
`/health` do not establish end-to-end deployment success.
# productivity-layer-ai
