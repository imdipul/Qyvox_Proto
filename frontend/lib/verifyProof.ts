import { getPrivateSessionToken } from "@/lib/supabaseClient";
import type { ProofBundle } from "@/lib/zkProver";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export interface ServerTraceStep {
  component: "policy" | "replay" | "verifier" | "database";
  operation: string;
  outcome: "passed" | "committed";
  duration_ms: number;
}

export interface ServerVerificationTrace {
  proof_system: "Groth16";
  curve: "BN254 / bn128";
  received_fields: ["proof", "publicSignals"];
  stored_fields: ["user_id", "verified_at", "proof_hash"];
  steps: ServerTraceStep[];
  total_ms: number;
}

export interface VerifyProgressEvent {
  component: "auth" | "transport";
  state: "running" | "passed";
  operation: string;
  duration_ms?: number;
}

export interface VerifyResult {
  verified: true;
  verified_at: string;
  trace: ServerVerificationTrace;
  client: {
    session_ms: number;
    round_trip_ms: number;
  };
}

/**
 * Submit a generated proof through an authenticated, proof-only request.
 * The JSON body is deliberately fixed to proof and publicSignals.
 */
export async function verifyProof(
  bundle: ProofBundle,
  onProgress?: (event: VerifyProgressEvent) => void,
): Promise<VerifyResult> {
  const sessionStarted = performance.now();
  onProgress?.({
    component: "auth",
    state: "running",
    operation: "Resolve a PII-free anonymous Supabase session",
  });
  const accessToken = await getPrivateSessionToken();
  const sessionMs = performance.now() - sessionStarted;
  onProgress?.({
    component: "auth",
    state: "passed",
    operation: "Resolve a PII-free anonymous Supabase session",
    duration_ms: sessionMs,
  });

  const requestStarted = performance.now();
  onProgress?.({
    component: "transport",
    state: "running",
    operation: "POST only proof + publicSignals to /api/v1/verify",
  });
  const response = await fetch(`${API_URL}/api/v1/verify`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${accessToken}`,
    },
    body: JSON.stringify({
      proof: bundle.proof,
      publicSignals: bundle.publicSignals,
    }),
  });

  const roundTripMs = performance.now() - requestStarted;
  const responseBody = (await response.json().catch(() => ({}))) as Partial<VerifyResult> & {
    detail?: string;
  };
  if (
    !response.ok ||
    responseBody.verified !== true ||
    typeof responseBody.verified_at !== "string" ||
    !responseBody.trace
  ) {
    throw new Error(responseBody.detail ?? "The verifier rejected this proof.");
  }

  onProgress?.({
    component: "transport",
    state: "passed",
    operation: "POST only proof + publicSignals to /api/v1/verify",
    duration_ms: roundTripMs,
  });

  return {
    verified: true,
    verified_at: responseBody.verified_at,
    trace: responseBody.trace,
    client: {
      session_ms: sessionMs,
      round_trip_ms: roundTripMs,
    },
  };
}
