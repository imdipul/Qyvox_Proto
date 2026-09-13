import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { groth16 } from "snarkjs";

const backendDirectory = dirname(fileURLToPath(import.meta.url));
const repositoryDirectory = resolve(backendDirectory, "..");
const apiUrl = process.env.QYVOX_TEST_API_URL ?? "http://127.0.0.1:8000";

function parseEnv(source) {
  return Object.fromEntries(
    source
      .split(/\r?\n/u)
      .map((line) => line.trim())
      .filter((line) => line && !line.startsWith("#") && line.includes("="))
      .map((line) => {
        const separator = line.indexOf("=");
        return [line.slice(0, separator).trim(), line.slice(separator + 1).trim()];
      }),
  );
}

async function readConfiguration() {
  const [frontendText, backendText] = await Promise.all([
    readFile(resolve(repositoryDirectory, "frontend/.env.local"), "utf8"),
    readFile(resolve(backendDirectory, ".env"), "utf8"),
  ]);
  const frontend = parseEnv(frontendText);
  const backend = parseEnv(backendText);
  const configuration = {
    supabaseUrl: frontend.NEXT_PUBLIC_SUPABASE_URL,
    publishableKey: frontend.NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY,
    serviceRoleKey: backend.SUPABASE_SERVICE_ROLE_KEY,
  };
  for (const [name, value] of Object.entries(configuration)) {
    assert(value, `Missing live-test configuration: ${name}`);
  }
  return configuration;
}

async function requestJson(url, init = {}) {
  const response = await fetch(url, init);
  const body = await response.json().catch(() => ({}));
  return { response, body };
}

async function createAnonymousSession(configuration) {
  const { response, body } = await requestJson(
    `${configuration.supabaseUrl}/auth/v1/signup`,
    {
      method: "POST",
      headers: {
        apikey: configuration.publishableKey,
        Authorization: `Bearer ${configuration.publishableKey}`,
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ data: {}, gotrue_meta_security: {} }),
    },
  );
  assert.equal(response.status, 200, `Anonymous sign-in failed with ${response.status}`);
  assert.equal(typeof body.access_token, "string", "Anonymous sign-in returned no access token");
  assert.equal(typeof body.user?.id, "string", "Anonymous sign-in returned no user ID");
  return { accessToken: body.access_token, userId: body.user.id };
}

async function generateProof() {
  const currentYear = new Date().getUTCFullYear();
  const result = await groth16.fullProve(
    { birthYear: String(currentYear - 26), currentYear: String(currentYear) },
    resolve(repositoryDirectory, "frontend/public/zk/age_check.wasm"),
    resolve(repositoryDirectory, "frontend/public/zk/age_check_final.zkey"),
  );
  return {
    proof: result.proof,
    publicSignals: result.publicSignals.map(String),
  };
}

async function cleanup(configuration, userId) {
  const adminHeaders = {
    apikey: configuration.serviceRoleKey,
    Authorization: `Bearer ${configuration.serviceRoleKey}`,
  };
  const receiptResponse = await fetch(
    `${configuration.supabaseUrl}/rest/v1/verified_users?user_id=eq.${encodeURIComponent(userId)}`,
    { method: "DELETE", headers: adminHeaders },
  );
  assert(
    receiptResponse.ok,
    `Test receipt cleanup failed with ${receiptResponse.status}`,
  );
  const userResponse = await fetch(
    `${configuration.supabaseUrl}/auth/v1/admin/users/${encodeURIComponent(userId)}`,
    { method: "DELETE", headers: adminHeaders },
  );
  assert(userResponse.ok, `Test user cleanup failed with ${userResponse.status}`);
}

const configuration = await readConfiguration();
let testUserId;

try {
  const health = await requestJson(`${apiUrl}/health`);
  assert.equal(health.response.status, 200);
  assert.deepEqual(health.body, { status: "ok" });

  const serviceStatus = await requestJson(`${apiUrl}/status`);
  assert.equal(serviceStatus.response.status, 200);
  assert.equal(serviceStatus.body.status, "operational");
  assert.equal(serviceStatus.body.verifier, "operational");
  assert.equal(serviceStatus.body.database, "operational");

  const session = await createAnonymousSession(configuration);
  testUserId = session.userId;
  const proofBundle = await generateProof();
  const serializedBundle = JSON.stringify(proofBundle);
  assert(!/birth|dob|ageYear/iu.test(serializedBundle), "Proof request contains a private-input key");

  const authorizedHeaders = {
    Authorization: `Bearer ${session.accessToken}`,
    "Content-Type": "application/json",
  };

  const directDatabaseHeaders = {
    apikey: configuration.publishableKey,
    Authorization: `Bearer ${session.accessToken}`,
    "Content-Type": "application/json",
  };
  const blockedRead = await fetch(
    `${configuration.supabaseUrl}/rest/v1/verified_users?select=user_id`,
    { headers: directDatabaseHeaders },
  );
  assert(
    [401, 403].includes(blockedRead.status),
    `Authenticated clients must not read receipts directly; received ${blockedRead.status}`,
  );
  const blockedWrite = await fetch(
    `${configuration.supabaseUrl}/rest/v1/verified_users`,
    {
      method: "POST",
      headers: directDatabaseHeaders,
      body: JSON.stringify({
        user_id: session.userId,
        proof_hash: "0".repeat(64),
      }),
    },
  );
  assert(
    [401, 403].includes(blockedWrite.status),
    `Authenticated clients must not write receipts directly; received ${blockedWrite.status}`,
  );

  const verified = await requestJson(`${apiUrl}/api/v1/verify`, {
    method: "POST",
    headers: authorizedHeaders,
    body: serializedBundle,
  });
  assert.equal(verified.response.status, 200);
  assert.equal(verified.body.verified, true);
  assert.equal(verified.body.trace.proof_system, "Groth16");
  assert.equal(verified.body.trace.curve, "BN254 / bn128");
  assert.deepEqual(verified.body.trace.received_fields, ["proof", "publicSignals"]);
  assert.deepEqual(verified.body.trace.stored_fields, ["user_id", "verified_at", "proof_hash"]);
  assert.deepEqual(
    verified.body.trace.steps.map((step) => step.component),
    ["policy", "replay", "verifier", "database"],
  );
  assert(
    verified.body.trace.steps.every((step) => Number.isFinite(step.duration_ms) && step.duration_ms >= 0),
    "Every backend trace step must contain a real non-negative duration",
  );
  assert(Number.isFinite(verified.body.trace.total_ms) && verified.body.trace.total_ms >= 0);

  const storedReceipt = await requestJson(
    `${configuration.supabaseUrl}/rest/v1/verified_users?select=*&user_id=eq.${encodeURIComponent(session.userId)}`,
    {
      headers: {
        apikey: configuration.serviceRoleKey,
        Authorization: `Bearer ${configuration.serviceRoleKey}`,
      },
    },
  );
  assert.equal(storedReceipt.response.status, 200);
  assert.equal(storedReceipt.body.length, 1);
  assert.deepEqual(
    Object.keys(storedReceipt.body[0]).sort(),
    ["proof_hash", "user_id", "verified_at"],
    "The database receipt must contain only the privacy-minimal columns",
  );

  const replay = await requestJson(`${apiUrl}/api/v1/verify`, {
    method: "POST",
    headers: authorizedHeaders,
    body: serializedBundle,
  });
  assert.equal(replay.response.status, 409);
  assert.equal(replay.body.detail, "This proof has already been used.");

  const staleStatement = structuredClone(proofBundle);
  staleStatement.publicSignals[1] = String(new Date().getUTCFullYear() + 1);
  const stale = await requestJson(`${apiUrl}/api/v1/verify`, {
    method: "POST",
    headers: authorizedHeaders,
    body: JSON.stringify(staleStatement),
  });
  assert.equal(stale.response.status, 403);

  const privateField = { ...proofBundle, birthYear: 2000 };
  const privateFieldResponse = await requestJson(`${apiUrl}/api/v1/verify`, {
    method: "POST",
    headers: authorizedHeaders,
    body: JSON.stringify(privateField),
  });
  assert.equal(privateFieldResponse.response.status, 422);

  const missingAuth = await requestJson(`${apiUrl}/api/v1/verify`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: serializedBundle,
  });
  assert.equal(missingAuth.response.status, 401);

  const oversized = await requestJson(`${apiUrl}/api/v1/verify`, {
    method: "POST",
    headers: authorizedHeaders,
    body: "x".repeat(40_000),
  });
  assert.equal(oversized.response.status, 413);

  const allowedPreflight = await fetch(`${apiUrl}/api/v1/verify`, {
    method: "OPTIONS",
    headers: {
      Origin: "http://localhost:3000",
      "Access-Control-Request-Method": "POST",
      "Access-Control-Request-Headers": "authorization,content-type",
    },
  });
  assert.equal(allowedPreflight.status, 200);
  assert.equal(
    allowedPreflight.headers.get("access-control-allow-origin"),
    "http://localhost:3000",
  );

  const deniedPreflight = await fetch(`${apiUrl}/api/v1/verify`, {
    method: "OPTIONS",
    headers: {
      Origin: "https://attacker.invalid",
      "Access-Control-Request-Method": "POST",
    },
  });
  assert.equal(deniedPreflight.status, 400);
  assert.equal(deniedPreflight.headers.get("access-control-allow-origin"), null);

  console.log("Qyvox live integration test passed: auth, proof, replay, RLS, storage minimization, validation, limits, and CORS.");
} finally {
  if (testUserId) await cleanup(configuration, testUserId);
}
