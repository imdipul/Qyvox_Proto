"use client";

import { FormEvent, useMemo, useState } from "react";
import { generateAgeProof, type ProofBundle } from "@/lib/zkProver";
import {
  verifyProof,
  type ServerVerificationTrace,
  type VerifyProgressEvent,
} from "@/lib/verifyProof";

type Stage = "idle" | "proving" | "authenticating" | "submitting" | "verified" | "error";
type TraceStatus = "running" | "passed" | "committed";

interface ExecutionEvent {
  id: string;
  component: "browser" | "auth" | "transport" | "policy" | "replay" | "verifier" | "database";
  operation: string;
  status: TraceStatus;
  durationMs?: number;
}

function messageFromUnknown(error: unknown): string {
  return error instanceof Error ? error.message : "An unexpected verification error occurred.";
}

function buttonLabel(stage: Stage): string {
  if (stage === "proving") return "Constructing private witness…";
  if (stage === "authenticating") return "Opening private session…";
  if (stage === "submitting") return "Verifying cryptographic proof…";
  if (stage === "verified") return "Eligibility verified";
  return "Generate private proof";
}

function formatDuration(durationMs?: number, status: TraceStatus = "passed"): string {
  if (durationMs === undefined) return status;
  if (durationMs < 1) return `${durationMs.toFixed(3)} ms`;
  if (durationMs < 100) return `${durationMs.toFixed(2)} ms`;
  return `${Math.round(durationMs)} ms`;
}

export function ProofDemo() {
  const currentYear = useMemo(() => new Date().getUTCFullYear(), []);
  const [birthYear, setBirthYear] = useState("");
  const [stage, setStage] = useState<Stage>("idle");
  const [message, setMessage] = useState("");
  const [traceEvents, setTraceEvents] = useState<ExecutionEvent[]>([]);
  const [proofBundle, setProofBundle] = useState<ProofBundle | null>(null);
  const [serverTrace, setServerTrace] = useState<ServerVerificationTrace | null>(null);
  const isBusy = stage === "proving" || stage === "authenticating" || stage === "submitting";
  const minimumBirthYear = currentYear - 120;
  const proofPayload = proofBundle
    ? JSON.stringify({ proof: proofBundle.proof, publicSignals: proofBundle.publicSignals }, null, 2)
    : "";

  function upsertTrace(event: ExecutionEvent) {
    setTraceEvents((current) => {
      const existingIndex = current.findIndex((item) => item.id === event.id);
      if (existingIndex === -1) return [...current, event];
      return current.map((item, index) => (index === existingIndex ? event : item));
    });
  }

  function recordNetworkProgress(event: VerifyProgressEvent) {
    if (event.component === "auth") setStage("authenticating");
    if (event.component === "transport") setStage("submitting");
    upsertTrace({
      id: event.component,
      component: event.component,
      operation: event.operation,
      status: event.state === "running" ? "running" : "passed",
      durationMs: event.duration_ms,
    });
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setMessage("");
    setProofBundle(null);
    setServerTrace(null);
    setTraceEvents([]);

    let privateBirthYear = Number(birthYear);
    if (!Number.isInteger(privateBirthYear) || privateBirthYear < minimumBirthYear || privateBirthYear > currentYear) {
      setStage("error");
      setMessage(`Enter a whole year between ${minimumBirthYear} and ${currentYear}.`);
      return;
    }
    if (currentYear - privateBirthYear < 18) {
      privateBirthYear = 0;
      setBirthYear("");
      setStage("error");
      setMessage("This birth year does not meet the 18+ eligibility policy.");
      return;
    }

    try {
      setTraceEvents([
        {
          id: "witness",
          component: "browser",
          operation: "Map the private value to the in-memory Circom witness",
          status: "passed",
        },
        {
          id: "prover",
          component: "browser",
          operation: "Execute groth16.fullProve() with WASM + proving key",
          status: "running",
        },
      ]);
      setStage("proving");
      const proverStarted = performance.now();
      const nextProofBundle = await generateAgeProof({ birthYear: privateBirthYear, currentYear });
      upsertTrace({
        id: "prover",
        component: "browser",
        operation: "Execute groth16.fullProve() with WASM + proving key",
        status: "passed",
        durationMs: performance.now() - proverStarted,
      });

      // Clear both state and the mutable local value before authentication or transport.
      setBirthYear("");
      privateBirthYear = 0;
      upsertTrace({
        id: "purge",
        component: "browser",
        operation: "Clear the private witness reference before any network request",
        status: "passed",
      });
      setProofBundle(nextProofBundle);

      const result = await verifyProof(nextProofBundle, recordNetworkProgress);
      for (const step of result.trace.steps) {
        upsertTrace({
          id: `server-${step.component}`,
          component: step.component,
          operation: step.operation,
          status: step.outcome,
          durationMs: step.duration_ms,
        });
      }
      setServerTrace(result.trace);
      setStage("verified");
      setMessage("18+ eligibility confirmed. This receipt was produced by the live verifier.");
    } catch (error) {
      setStage("error");
      setMessage(messageFromUnknown(error));
    } finally {
      privateBirthYear = 0;
      setBirthYear("");
    }
  }

  return (
    <div className="verifier-stage" id="verifier">
      <section className="proof-card" aria-labelledby="verifier-title">
        <div className="card-kicker">
          <span><span className="live-dot" aria-hidden="true" />Local prover ready</span>
          <span className="record-id">QX / 001</span>
        </div>

        <div className="card-heading">
          <div><p>PRIVATE COMPUTATION</p><h2 id="verifier-title">Verify 18+ eligibility</h2></div>
          <div className="cipher-seal" aria-hidden="true"><span>zk</span></div>
        </div>

        <form onSubmit={handleSubmit} noValidate>
          <div className="field-row"><label htmlFor="birthYear">Birth year</label><span>never uploaded</span></div>
          <div className="input-shell">
            <input
              id="birthYear"
              name="birthYear"
              type="number"
              inputMode="numeric"
              autoComplete="off"
              min={minimumBirthYear}
              max={currentYear}
              step="1"
              placeholder="1998"
              value={birthYear}
              onChange={(changeEvent) => {
                setBirthYear(changeEvent.target.value);
                if (stage !== "idle") {
                  setStage("idle");
                  setMessage("");
                  setTraceEvents([]);
                  setProofBundle(null);
                  setServerTrace(null);
                }
              }}
              disabled={isBusy}
              aria-describedby="birthYear-help proof-status"
              required
            />
            <span className="device-chip">DEVICE MEMORY</span>
          </div>
          <p className="field-help" id="birthYear-help">Used once as a private circuit witness, then cleared.</p>
          <button type="submit" disabled={isBusy || birthYear.length === 0}>
            <span>{buttonLabel(stage)}</span>
            {isBusy ? <span className="spinner" aria-hidden="true" /> : <span aria-hidden="true">↗</span>}
          </button>
        </form>

        <ol className="proof-progress" data-stage={stage} aria-label="Verification stages">
          <li><span>01</span><div><strong>Witness</strong><small>Stays in browser</small></div></li>
          <li><span>02</span><div><strong>Proof</strong><small>Groth16 / bn128</small></div></li>
          <li><span>03</span><div><strong>Verdict</strong><small>Eligibility only</small></div></li>
        </ol>

        <div id="proof-status" className={`result ${stage === "verified" ? "success" : stage === "error" ? "failure" : ""}`} role="status" aria-live="polite">
          <span className="result-mark" aria-hidden="true">{stage === "verified" ? "✓" : stage === "error" ? "!" : "◆"}</span>
          <span>{message || "The outgoing JSON contains only proof and public signals."}</span>
        </div>

        <section className={`execution-receipt ${traceEvents.length > 0 ? "is-active" : ""}`} aria-labelledby="execution-title">
          <div className="execution-head">
            <div><span>LIVE EVIDENCE</span><h3 id="execution-title">Actual execution receipt</h3></div>
            <strong>{serverTrace ? `${formatDuration(serverTrace.total_ms)} server` : "awaiting run"}</strong>
          </div>

          {traceEvents.length === 0 ? (
            <p className="execution-empty">Run a proof to capture the browser, API, verifier, and database path from this request.</p>
          ) : (
            <ol className="execution-trace" aria-live="polite">
              {traceEvents.map((traceEvent) => (
                <li key={traceEvent.id} data-status={traceEvent.status}>
                  <span className="trace-component">{traceEvent.component}</span>
                  <span className="trace-operation">{traceEvent.operation}</span>
                  <strong>{formatDuration(traceEvent.durationMs, traceEvent.status)}</strong>
                </li>
              ))}
            </ol>
          )}

          {serverTrace && (
            <div className="receipt-boundary">
              <span><small>API received</small>{serverTrace.received_fields.join(" + ")}</span>
              <span><small>Database stored</small>{serverTrace.stored_fields.join(" + ")}</span>
            </div>
          )}

          {proofBundle && (
            <details className="payload-inspector">
              <summary>
                <span>Inspect the exact proof-only request</span>
                <strong>{proofPayload.length.toLocaleString()} bytes</strong>
              </summary>
              <p>Authorization headers are intentionally excluded. No private witness field exists in this JSON.</p>
              <pre><code>{proofPayload}</code></pre>
            </details>
          )}

          <p className="receipt-disclaimer">Browser timings use this tab&apos;s performance clock. Server timings are measured by FastAPI and returned after verification; no step is simulated.</p>
        </section>
      </section>
      <p className="stage-caption"><span>Privacy field / active</span><strong>{currentYear} policy epoch</strong></p>
    </div>
  );
}
