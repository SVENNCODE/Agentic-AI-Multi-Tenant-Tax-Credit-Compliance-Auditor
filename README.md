# Agentic AI Multi-Tenant Tax Credit and Compliance Auditor

## Project Overview

An agentic tax-preparation assistant for international students. It extracts and cross-validates a user's tax information with LLM agents, runs it through a deterministic IRS residency and credit-eligibility engine, and produces a document checklist and plain-language explanation of the results. It does not prepare or file tax returns and does not provide legal or tax advice.

## Key Features

- Three-agent LangGraph pipeline: LLM agents extract and cross-validate inputs, then hand off to a deterministic rules engine for eligibility decisions. The LLM never decides eligibility; it only extracts and explains.
- Deterministic IRS Substantial Presence Test (Publication 519) engine, including an explicit `UNDETERMINED` status for ambiguous or conflicting inputs rather than a silent wrong answer.
- Plugin-based treaty and credit eligibility engine covering AOTC, the Lifetime Learning Credit, the NJ tuition deduction, and the US-India treaty (Article 21(2)), structured so additional country treaties can be added as isolated plugins.
- Multi-tenant data isolation enforced at the database layer with Postgres Row Level Security, not application logic alone.
- Atomic, transaction-safe writes for credit evaluations and visa status periods using `SECURITY INVOKER` Postgres RPC functions with advisory locking, replacing delete-then-insert races.
- Hardened FastAPI backend: JWKS-based JWT verification restricted to asymmetric algorithms, per-user rate limiting, request body size limits, and a locked-down CORS policy.
- Dedicated Audit and Credit Discovery Hub and Readiness Report / Action Center screens, separate from the questionnaire flow.
- Dockerized frontend and backend with a docker-compose stack for local development.
- Backend test suite of 55+ pytest cases plus a PGlite-based harness that applies the Postgres migrations and exercises RLS and RPC behavior in isolation.

## Prerequisites & Dependencies

- Node.js 22 or later
- Python 3.11 or later
- Docker and Docker Compose, if running the containerized stack
- A Supabase project (Postgres and Auth)
- An Anthropic API key
- The Supabase CLI, if applying database migrations

## Installation & Setup

### Option 1: Docker Compose

1. Clone the repository.
   ```bash
   git clone https://github.com/SVENNCODE/Agentic-AI-Multi-Tenant-Tax-Credit-Compliance-Auditor.git
   cd Agentic-AI-Multi-Tenant-Tax-Credit-Compliance-Auditor
   ```
2. Copy the environment template and fill in real values.
   ```bash
   cp env.docker.example .env
   ```
3. Build and start both services.
   ```bash
   docker compose up --build
   ```
4. Open `http://localhost:3000`. The API is available at `http://localhost:8000`.

### Option 2: Local development

1. Clone the repository and enter it.
   ```bash
   git clone https://github.com/SVENNCODE/Agentic-AI-Multi-Tenant-Tax-Credit-Compliance-Auditor.git
   cd Agentic-AI-Multi-Tenant-Tax-Credit-Compliance-Auditor
   ```
2. Install and run the backend.
   ```bash
   cd backend
   python -m venv venv
   venv\Scripts\activate   # or: source venv/bin/activate on macOS/Linux
   pip install -r requirements.txt
   cp .env.example .env    # then fill in real values
   uvicorn app.main:app --reload
   ```
3. In a separate terminal, install and run the frontend.
   ```bash
   cd ai-audit-agent
   npm install
   cp .env.example .env.local   # then fill in real values
   npm run dev
   ```
4. Open `http://localhost:3000`.

### Applying database migrations

Migrations live in `supabase/migrations/`. Against a linked Supabase project:

```bash
supabase login
supabase link --project-ref <your-project-ref>
supabase db push
```

## Usage Examples

1. Create an account on the signup page and sign in.
2. Complete the residency and tax questionnaire.
3. Review the residency status and evaluated credits on the Audit and Credit Discovery Hub.
4. Check outstanding items and the filing readiness checklist on the Action Center.

Example direct API call to the backend (requires a valid Supabase session token):

```bash
curl -X GET "http://localhost:8000/api/v1/audit/summary" \
  -H "Authorization: Bearer <supabase-access-token>"
```

## Configuration / Environment Variables

Full templates are provided in `backend/.env.example` and `ai-audit-agent/.env.example`. Do not commit the real `.env` or `.env.local` files.

### Backend (`backend/.env`)

| Variable                    | Description                                                                      |
| --------------------------- | -------------------------------------------------------------------------------- |
| `SUPABASE_URL`              | Supabase project URL.                                                            |
| `SUPABASE_ANON_KEY`         | Public anon or publishable key, used to build per-user RLS-scoped clients.       |
| `SUPABASE_SERVICE_ROLE_KEY` | Server-only key that bypasses RLS. Never expose to the browser.                  |
| `ANTHROPIC_API_KEY`         | Server-only Anthropic API key.                                                   |
| `ALLOWED_ORIGINS`           | Comma-separated list of browser origins allowed to call the API.                 |
| `ENABLE_API_DOCS`           | Set to `true` only in local development to expose `/docs` and `/openapi.json`.   |
| `QUESTIONNAIRE_RATE_LIMIT`  | Rate limit applied to `POST /api/v1/questionnaire/save`, for example `5/minute`. |
| `MAX_REQUEST_BODY_BYTES`    | Maximum accepted request body size in bytes.                                     |
| `TEST_USER_ID`              | Used only by the manual integration scripts.                                     |

### Frontend (`ai-audit-agent/.env.local`)

| Variable                               | Description                                                                            |
| -------------------------------------- | -------------------------------------------------------------------------------------- |
| `NEXT_PUBLIC_SITE_URL`                 | Public site URL, used for auth redirects.                                              |
| `NEXT_PUBLIC_API_URL`                  | Backend base URL including the API prefix, for example `http://localhost:8000/api/v1`. |
| `NEXT_PUBLIC_SUPABASE_URL`             | Supabase project URL.                                                                  |
| `NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY` | Public Supabase key, embedded in browser JavaScript.                                   |

## Running Tests

Backend:

```bash
cd backend
pytest
```

Database migrations and Row Level Security policies (PGlite harness):

```bash
cd supabase/tests
npm install
node db.test.mjs ../migrations
```
Screen 1 - Login
<img width="1917" height="903" alt="Screenshot 2026-09-24 235740" src="https://github.com/user-attachments/assets/886edb01-de44-4dd3-be16-abe2d37458b0" />

Screen 1.5 - SignUp
<img width="1917" height="906" alt="Screenshot 2026-09-25 001910" src="https://github.com/user-attachments/assets/07f73a41-2f4c-4c8d-8371-4776b35d351b" />

Screen 2 - Profile
<img width="1897" height="907" alt="Screenshot 2026-09-25 000350" src="https://github.com/user-attachments/assets/772612ad-5336-4cdd-adf3-8ed2c7c5b2a7" />

Screen 3 - Income
<img width="1917" height="910" alt="Screenshot 2026-09-25 000436" src="https://github.com/user-attachments/assets/e9106cbb-bbad-49bf-af0f-4c2b93c7016e" />

Screen 4 - Expenses
<img width="1917" height="907" alt="Screenshot 2026-09-25 000508" src="https://github.com/user-attachments/assets/80a7247c-bee8-40d0-862c-21a7f48d260e" />

Screen 4.5 - Education Expenses
<img width="1892" height="903" alt="Screenshot 2026-09-25 000535" src="https://github.com/user-attachments/assets/2b383620-cc03-4dc8-94a0-d9d63d430928" />

Screen 5 - Review and Submit
<img width="1915" height="907" alt="Screenshot 2026-09-25 000615" src="https://github.com/user-attachments/assets/5f6fc37b-3036-44fb-b6bd-0eb5f653209c" />

Screen 6 -  DashBoard
<img width="1900" height="903" alt="Screenshot 2026-09-25 000931" src="https://github.com/user-attachments/assets/67d7aefa-b317-45c9-bff0-6508517950f0" />

Screen 7 - Credit Hub
<img width="1900" height="911" alt="Screenshot 2026-09-25 001013" src="https://github.com/user-attachments/assets/379fc661-8576-48d4-a0a8-17fec8f332f1" />

Screen 8 - Action Center
<img width="1917" height="908" alt="Screenshot 2026-09-25 001039" src="https://github.com/user-attachments/assets/b8c725ad-8615-430c-b923-427b3bdcba28" />

## License

MIT License. See LICENSE for the full text.
