# Empório da Música Agent

Python customer-service agent for the fictional store Empório da Música. It answers
questions about instruments, stock, prices, promotions, orders, and store policies
without giving the model direct access to SQL, files, or customer records.

The full design lives in [`artefatos_projeto/SDD.md`](artefatos_projeto/SDD.md).
Sample conversations live in [`examples/conversations.md`](examples/conversations.md).

The assistant replies to customers in Brazilian Portuguese. This README is in English
for the take-home review.

Public repository: https://github.com/erosgri/emporio-da-musica-agent

## How to run

### Requirements

- Python 3.11 or newer
- An API key from a provider that supports function calling:
  - OpenAI (`gpt-4.1-mini`, the challenge reference), or
  - Gemini on Google AI Studio (free tier for local testing)

### Installation

With `pip`:

```bash
python -m pip install -e ".[dev]"
```

With `uv`:

```bash
uv sync --extra dev
```

Copy the environment file.

PowerShell:

```powershell
Copy-Item .env.example .env
```

Linux or macOS:

```bash
cp .env.example .env
```

### Model provider

#### OpenAI (challenge reference)

```dotenv
OPENAI_API_KEY=your-openai-key
EMPORIO_MODEL=gpt-4.1-mini
```

The account needs prepaid credits. Without balance, the API returns 429 and the chat
tells the user the provider refused the request.

#### Gemini (free local testing)

The OpenAI API has no free model. To test without a credit card, use Google AI Studio:

1. Create a key at [Google AI Studio](https://aistudio.google.com/apikey).
2. Fill in `.env`:

```dotenv
OPENAI_API_KEY=your-gemini-key
EMPORIO_MODEL=gemini-3.5-flash-lite
EMPORIO_OPENAI_BASE_URL=https://generativelanguage.googleapis.com/v1beta/openai/
```

The variable is still named `OPENAI_API_KEY` because the SDK talks the OpenAI-compatible
contract. The challenge reference model remains `gpt-4.1-mini`.

During local testing, `gemini-2.5-flash` was rejected for new accounts and
`gemini-3.8-flash` timed out. `gemini-3.5-flash-lite` was the free model that completed
the tool-calling loop.

### Environment variables

| Variable | Purpose | Default |
|---|---|---|
| `OPENAI_API_KEY` | Provider key (OpenAI or Gemini) | empty |
| `EMPORIO_MODEL` | Model name | `gpt-4.1-mini` |
| `EMPORIO_OPENAI_BASE_URL` | Alternative base URL | empty (official OpenAI API) |
| `EMPORIO_STRUCTURED_OUTPUT` | Force or disable `json_schema` | automatic |
| `EMPORIO_LOG_LEVEL` | Log level | `INFO` |
| `EMPORIO_MAX_TOOL_ROUNDS` | Function-calling rounds | `4` |
| `EMPORIO_MAX_TOOL_CALLS` | Tool-call cap per turn | `8` |

An empty base URL is ignored. When `EMPORIO_OPENAI_BASE_URL` is set, OpenAI structured
JSON output is turned off automatically, because compatible providers do not always
accept `response_format=json_schema` together with tools.

### Web UI

```bash
python -m streamlit run app.py
```

Open [http://localhost:8501](http://localhost:8501). On first run, the CSVs are
validated and imported into `data/processed/emporio.db`, and the PDF is indexed into
`data/processed/policy_chunks.json`. Both artifacts are rebuilt when the source file
changes.

You can also paste a key in the sidebar, but the model and base URL come from `.env`.
Restart Streamlit after changing `.env`.

### Terminal

```bash
emporio-cli
```

Type `sair` to quit.

### Tests and quality

```bash
python -m pytest --cov=emporio_agent --cov-report=term-missing
python -m ruff check .
python -m mypy src
```

GitHub Actions runs lint, mypy, and pytest with a 75% coverage gate.

## Architecture

The solution is hybrid:

1. Function calling for catalog, price, promotion, payment, and order data.
2. Lexical BM25 RAG only for the store-policy PDF.
3. An LLM to interpret intent, pick tools, and write the customer-facing answer.
4. Response validation before anything is shown to the customer.

```text
Customer message
        |
        v
Orchestrator (function calling)
        |
        +--> catalog / promotions / payment --> read-only SQLite
        |
        +--> orders ---------------------------> read-only SQLite
        |
        +--> policies -------------------------> BM25 index of the PDF
        |
        v
Guardrails (contracts + evidence)
        |
        v
Reply to the customer
```

There is no generic SQL, file, or code-execution tool. The model only sees closed
interfaces.

## Technical decisions

### Framework and UI

Python was chosen for the LLM, data, and testing ecosystem. Streamlit covers the demo
chat with little UI code. A CLI uses the same orchestrator so rules are not duplicated.
FastAPI would be a better channel API, but the brief asks for a demonstrable
conversational prototype, not a production backend.

### Why hybrid, not pure RAG, generic ReAct, or a SQL agent

- Pure RAG cannot guarantee exact prices, stock, or order status.
- Open-ended ReAct lets the model improvise steps and increases hallucination.
- A SQL agent exposes the database and makes queries unpredictable.

Function calling with specific tools keeps structured data exact. RAG is limited to the
normative text in the PDF.

### LLM

The reference provider is OpenAI `gpt-4.1-mini`: stable function calling, low latency,
and a cost that fits a take-home. The official `openai` SDK is used explicitly, without
LangChain, so the tool loop stays visible in the code.

The model name and base URL are configurable. Gemini is only a free testing alternative,
through the OpenAI-compatible endpoint. Business rules do not change with the provider.

### Retrieval

RAG indexes only `políticas_da_loja.pdf`. Products, orders, and promotions stay out of
the index.

BM25 (`rank-bm25`) was chosen because the manual is small, local, and must be citable.
Lexical search explains the returned excerpt, does not need paid embeddings, and keeps
negations, deadlines, and percentages. Chunks follow document sections and never mix
different policies. Each evidence item includes section and page.

With more time, the natural next step would be hybrid search (BM25 + embeddings) if
evaluation showed failures on very indirect questions.

### Prompt strategy

The system prompt defines the persona, Brazilian Portuguese tone, and the obligation to
use tools for store facts. It is not the main safety barrier.

Critical guardrails live in code:

- Pydantic contracts on tools (`extra="forbid"`)
- available = `status == "active"` and stock > 0
- promotions only when `is_active = true`
- the 5% PIX discount does not stack with a promotion
- an order lookup requires `order_id` plus a full email or phone number
- factual questions need evidence in the final answer
- caps on tool rounds and tool calls
- fail closed: without evidence, the agent asks for clarification or hands off to a human

The model is expected to return a `GroundedResponse` JSON object. With OpenAI, that is
enforced through `json_schema`. With Gemini, the parser accepts partial JSON or plain
text after tools have already run, and attaches the real evidence from that turn.

### Data and rules

Local SQLite avoids Pandas and ad-hoc queries. Ingestion validates the CSVs, materializes
the database, and leaves serving read-only. Money uses `Decimal`. Historical order totals
are not recalculated.

Inconsistencies in the source data are documented rather than silently “fixed”:

- the catalog has 65 products; the manual says “300+”
- active products can have zero stock
- IDs 135–144 disagree across name, description, and specs
- there is a general phone number and a separate WhatsApp number
- the general installment wording disagrees with the detailed rule; the detail wins
- promotions have no start/end dates; `is_active` is the source of truth

## Tools

| Tool | Use |
|---|---|
| `search_products` | List instruments by text, category, price, and filters |
| `get_product` | Detail, stock, and promotion for one item |
| `calculate_purchase_options` | Promotion, PIX, and installments |
| `get_order_status` | Order lookup after identity checks |
| `search_store_policy` | Citable excerpts from the manual |
| `get_store_information` | Address, hours, phone, WhatsApp, email, and catalog scope |

Skills covered: discovery, details/comparison, price/payment, order tracking, policies,
store information, out-of-scope, and conversation continuity.

## Known limitations

What the prototype does not do:

- purchase, cancellation, refund, or opening a real support ticket
- integration with WhatsApp, ERP, live inventory, or carriers
- strong order authentication; the check fits the CSV, not production
- conversation persistence beyond the session
- semantic RAG; very indirect policy questions may need rephrasing
- a guarantee that every free model will return complete JSON; the parser tolerates
  that after tools run, but quality varies
- the chat depends on the provider’s key, quota, and latency

What I would do with more time:

1. Automated conversation evaluation with gold cases (catalog, PIX, order, policy) and
   a grounding metric, not just fluency.
2. Hybrid PDF search if BM25 fails on paraphrases.
3. FastAPI as the single channel, with Streamlit and WhatsApp as clients.
4. Order authentication via a possession challenge, instead of email/phone in chat.
5. Observability: traces per turn, tool used, evidence used, and refusals.
6. Human handoff with the session context.
7. PostgreSQL and sync if the catalog stopped being a static dump.

## Use of coding assistants

Development was done in **Cursor**, with the coding agent in the local repository. I did
not use Copilot, Claude.ai, or ChatGPT as the main implementation environment.

Workflow:

1. **Read the brief and the data first.** The agent analyzed the challenge PDF, the
   store manual, and the CSVs before writing code. Inconsistencies (catalog vs. “300+
   products”, two phone numbers, PIX vs. promotion) were recorded in the SDD.
2. **SDD first.** Architecture, tools, skills, RAG contracts, guardrails, and tests were
   defined in `artefatos_projeto/SDD.md`. Implementation followed that document; it did
   not start from an improvised chat.
3. **Incremental implementation.** Scaffold, SQLite ingestion, BM25, tools, orchestrator,
   Streamlit, tests, and CI. Price, stock, and order rules stayed in deterministic
   Python on purpose: the model does not compute PIX or invent availability.
4. **Tests as the contract.** Pytest covers ingestion, availability, promotions, PIX,
   installments, orders, policies, and grounding guardrails. Ruff and mypy run in CI.
5. **Debug against the real runtime.** Execution failures (empty base URL pointing at
   OpenAI, an account with no credits, an unavailable Gemini model, `thought_signature`,
   and incomplete JSON) were reproduced against the API and fixed in code, not papered
   over in the UI.

Human decisions: the hybrid architecture, rejecting a SQL agent, the closed tool list,
fail-closed behavior without evidence, and the store tone. Cursor sped up reading the
artifacts, boilerplate, tests, and iteration. Commercial behavior does not depend on
the coding model’s suggestions or on the serving LLM.

## Layout

```text
.
├── app.py
├── artefatos_projeto/
│   ├── SDD.md
│   ├── políticas_da_loja.pdf
│   └── *.csv
├── examples/
│   └── conversations.md
├── src/emporio_agent/
├── tests/
├── data/processed/
└── .github/workflows/ci.yml
```
