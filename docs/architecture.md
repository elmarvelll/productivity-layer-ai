# Source audit and runtime contract

Extracted from the sibling `../akadverse` checkout on 17 November 2026. Runtime
source, tool definitions, dependency pins and existing Python tests were copied
from `akadverse-productivity-ai`, excluding secrets, virtualenvs and caches.
The original AkadVerse repository is not modified by this extraction.

## Request flow

1. The signed-in browser sends a stable request ID to AkadVerse's assistant route.
2. AkadVerse checks ownership, persists the message, acquires a 90-second turn
   lease, and signs two short-lived RS256 tokens bound to student/conversation/turn.
3. AkadVerse calls `POST /api/v1/assistant/chat` with a Python-audience bearer
   token, `X-Productivity-Service-Token`, and JSON containing `conversation_id`,
   `turn_id`, `callback_token` (the separate backend-audience token).
4. Python checks both token audiences, issuer, key ID, expiry and binding. It fetches
   context from the fixed AkadVerse origin, then runs Gemini function calling.
5. Every selected operation is validated against `app/tools/definitions.json`.
   Python posts `{action:"tool", step, name, arguments}` to
   `/api/productivity/assistant/service`; context uses `{action:"context"}`.
   Both callbacks carry the service secret and backend bearer token.
6. AkadVerse validates again, applies ownership/domain rules, and persists actual
   execution results. Python feeds those results to Gemini for the final response.
7. Sensitive operations return `awaiting_confirmation` and stop the agent. Only
   the student's authenticated Confirm control can execute the proposal.

Python also exposes a delegated active-turn context read at
`GET /api/v1/assistant/conversations/{conversation_id}`. It requires the normal
service/delegation headers plus `X-Productivity-Callback-Token`. General browser
conversation history continues to come from AkadVerse.

## Responsibilities preserved

- `app/agent/prompts.py`: PIP identity, timezone rules, clarification requirements,
  supported operations and restrictions against invented success.
- `app/agent/orchestrator.py`: bounded tool loop, call IDs, thought signatures,
  duplicate-write protection, confirmation stops and safe handling of unknown outcomes.
- `app/tools/`: full tool schemas and JSON Schema validation.
- `app/integrations/gemini.py`: provider schema adaptation and explicit function execution.
- `app/integrations/akadverse.py`: fixed callback destination, no redirects, 512 KB
  response limit, safe backend error correlation, no automatic write retries.
- `app/security.py`, `app/middleware.py`: delegated authentication and bounded bodies.
- `app/main.py`: API routes, whole-turn deadline and redacted failure responses.

Supported tools cover ordinary tasks and scheduled work slots, recurring habits
and outcomes, personal events/categories/backups, read-only official classes,
bounded task/schedule analytics, and account timezone preferences. The authoritative
list and argument constraints are in `app/tools/definitions.json`.

Reminders, official timetable edits, attendance writes, ordinary-task reopening,
general personal-event completion, bulk import, arbitrary SQL and arbitrary HTTP
are not registered capabilities. Voice capture/transcription remains in AkadVerse
and sends editable text to the assistant, not microphone bytes to Python.

## Backend compatibility

The companion logic was inspected in AkadVerse's
`services/productivity-layer/assistant/{service,security,schema,tools,store}.ts`
and `src/app/api/productivity/assistant/{route.ts,service/route.ts}`.
It remains in AkadVerse because moving it would remove the authenticated authority
and transaction boundary for the existing productivity data.

Backend receipts, stable operation identities, ownership checks, stale-target
checks and confirmation expiry remain authoritative. Confirming one proposal does
not automatically resume a longer multi-step request. Unknown writes require
receipt reconciliation rather than another Gemini write attempt.

Keep `app/tools/definitions.json` synchronized with AkadVerse's embedded copy.
Changes to route paths, JWT audiences (`akadverse-productivity-ai` and
`akadverse-productivity-backend`), issuer (`akadverse-productivity`), envelopes,
operation identities or tool schemas require coordinated backend changes.
