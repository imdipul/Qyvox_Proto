import assert from "node:assert/strict";
import { spawn } from "node:child_process";
import { fileURLToPath } from "node:url";
import { dirname, resolve } from "node:path";
import { groth16 } from "snarkjs";

const circuitDirectory = dirname(fileURLToPath(import.meta.url));
const repositoryDirectory = resolve(circuitDirectory, "..");
const wasmPath = resolve(circuitDirectory, "build/age_check_js/age_check.wasm");
const zkeyPath = resolve(circuitDirectory, "build/age_check_final.zkey");
const verificationKeyPath = resolve(circuitDirectory, "build/verification_key.json");

const eligibleResult = await groth16.fullProve(
  { birthYear: "2000", currentYear: "2026" },
  wasmPath,
  zkeyPath,
);

assert.deepEqual(
  eligibleResult.publicSignals,
  ["1", "2026"],
  "Public signals must remain [isEligible, currentYear]",
);

const valid = await groth16.verify(
  JSON.parse(await (await import("node:fs/promises")).readFile(verificationKeyPath, "utf8")),
  eligibleResult.publicSignals,
  eligibleResult.proof,
);
assert.equal(valid, true, "A qualifying witness must produce a valid proof");

const boundaryResult = await groth16.fullProve(
  { birthYear: "2008", currentYear: "2026" },
  wasmPath,
  zkeyPath,
);
assert.deepEqual(
  boundaryResult.publicSignals,
  ["1", "2026"],
  "A witness exactly 18 calendar years earlier must satisfy the policy",
);

const tamperedSignals = [...eligibleResult.publicSignals];
tamperedSignals[1] = "2027";
assert.equal(
  await groth16.verify(
    JSON.parse(await (await import("node:fs/promises")).readFile(verificationKeyPath, "utf8")),
    tamperedSignals,
    eligibleResult.proof,
  ),
  false,
  "Changing a public year must invalidate the proof",
);

const originalConsoleError = console.error;
try {
  // Witness generation logs its expected constraint failure before rejecting;
  // silence only that known-negative branch to keep CI output unambiguous.
  console.error = () => {};
  await assert.rejects(
    () => groth16.fullProve(
      { birthYear: "2010", currentYear: "2026" },
      wasmPath,
      zkeyPath,
    ),
    "An under-18 witness must not satisfy the circuit",
  );
  await assert.rejects(
    () => groth16.fullProve(
      { birthYear: "2027", currentYear: "2026" },
      wasmPath,
      zkeyPath,
    ),
    "A future birth year must not exploit finite-field subtraction",
  );
  await assert.rejects(
    () => groth16.fullProve(
      { birthYear: "65517", currentYear: "65536" },
      wasmPath,
      zkeyPath,
    ),
    "A public year outside the circuit's 16-bit range must be rejected",
  );
} finally {
  console.error = originalConsoleError;
}

// Exercise the exact helper that FastAPI invokes in production.
const verifier = await new Promise((resolvePromise, rejectPromise) => {
  const child = spawn(
    process.execPath,
    [
      resolve(repositoryDirectory, "backend/verify.mjs"),
      resolve(repositoryDirectory, "backend/zk/verification_key.json"),
    ],
    { cwd: resolve(repositoryDirectory, "backend") },
  );
  let stdout = "";
  let stderr = "";
  const timeout = setTimeout(() => {
    child.kill("SIGKILL");
    rejectPromise(new Error("Backend verifier smoke test timed out"));
  }, 20_000);

  child.stdout.setEncoding("utf8");
  child.stderr.setEncoding("utf8");
  child.stdout.on("data", (chunk) => { stdout += chunk; });
  child.stderr.on("data", (chunk) => { stderr += chunk; });
  child.on("error", rejectPromise);
  child.on("close", (code) => {
    clearTimeout(timeout);
    if (code !== 0) {
      rejectPromise(new Error(stderr || `Verifier exited with code ${code}`));
      return;
    }
    resolvePromise(JSON.parse(stdout));
  });

  child.stdin.end(JSON.stringify({
    proof: eligibleResult.proof,
    publicSignals: eligibleResult.publicSignals,
  }));
});
assert.deepEqual(verifier, { valid: true });

console.log("Qyvox circuit smoke test passed.");
// SnarkJS's worker pool can keep Node's event loop open after all assertions.
// The test has no pending application work, so terminate deterministically.
process.exit(0);
