# Qyvox

Qyvox is a privacy-preserving age-verification engine. A Circom circuit proves
that a private birth year is at least 18 years before a server-enforced public
year. Proof generation happens in the browser; the FastAPI service receives
only a Groth16 proof and its public signals.

## Repository map

- `circuits/` — Circom source and the reproducible development trusted setup.
- `frontend/` — Next.js App Router client and browser-side SnarkJS prover.
- `backend/` — FastAPI verifier, Supabase Auth validation, replay detection,
  and the minimal verification record.
- `supabase/` — PostgreSQL schema. It deliberately contains no birth year, date
  of birth, or age column.

## Local setup

Prerequisites: Node.js 22+, Python 3.12+, Circom 2.x, and OpenSSL.

1. Build the circuit artifacts:

   ```bash
   cd circuits
   npm ci
   ./setup.sh
   ```

2. Create a Supabase project, enable anonymous sign-ins, and run
   `supabase/schema.sql` in its SQL editor.
3. Copy `frontend/.env.example` to `frontend/.env.local` and
   `backend/.env.example` to `backend/.env`, then enter the project values.
4. Start the API:

   ```bash
   cd backend
   npm ci
   python -m venv .venv
   . .venv/bin/activate
   pip install -r requirements.txt
   uvicorn main:app --reload --port 8000
   ```

5. Start the web app:

   ```bash
   cd frontend
   npm ci
   npm run dev
   ```

## Validation

Run the deterministic checks before using the live integration suite:

```bash
cd circuits && npm test
cd ../backend && .venv/bin/pip install -r requirements-dev.txt
.venv/bin/python -W error -m unittest -v
cd ../frontend && npm run lint && npm run build
```

With the frontend, API, and configured Supabase project running, exercise the
real anonymous-auth, proof, replay, RLS, storage-minimization, request-limit,
and CORS path. The test creates an isolated anonymous user and receipt and
removes both in a `finally` cleanup:

```bash
cd backend
npm run test:live
```

## Security boundary

The browser sends a Supabase access token in the `Authorization` header and a
JSON body containing exactly `proof` and `publicSignals`. It never includes the
birth year. The API verifies the token, requires `isEligible == 1`, requires the
public year to match its UTC year, verifies the Groth16 proof, and stores only
the authenticated user ID, verification timestamp, and proof fingerprint.

This requested two-input circuit proves knowledge of *some* qualifying birth
year; on its own it cannot prove that the witness is the user's truthful,
government-issued birth year. Calendar-year arithmetic also treats everyone
born in the same year alike. A real civil-service deployment must add an
issuer-signed credential commitment, exact date arithmetic, revocation, and a
server challenge bound into the circuit. The current implementation is a
complete, runnable cryptographic baseline, not a substitute for that issuer
trust layer.

The included setup performs a one-machine development ceremony. Production
must use a recognized multi-party Powers of Tau transcript and a publicly
auditable circuit-specific contribution ceremony.
