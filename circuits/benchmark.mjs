import { performance } from "node:perf_hooks";
import { readFile, stat } from "node:fs/promises";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { spawnSync } from "node:child_process";
import { groth16 } from "snarkjs";

const circuitDirectory = dirname(fileURLToPath(import.meta.url));
const wasmPath = resolve(circuitDirectory, "build/age_check_js/age_check.wasm");
const zkeyPath = resolve(circuitDirectory, "build/age_check_final.zkey");
const vkeyPath = resolve(circuitDirectory, "build/verification_key.json");
const input = { birthYear: "2000", currentYear: "2026" };

const round = (value) => Math.round(value * 100) / 100;
const percentile = (values, fraction) => {
  const ordered = [...values].sort((a, b) => a - b);
  return ordered[Math.min(ordered.length - 1, Math.ceil(ordered.length * fraction) - 1)];
};

const verificationKey = JSON.parse(await readFile(vkeyPath, "utf8"));
const provingSamples = [];
let latestProof;

for (let index = 0; index < 5; index += 1) {
  const started = performance.now();
  latestProof = await groth16.fullProve(input, wasmPath, zkeyPath);
  provingSamples.push(performance.now() - started);
}

const verificationSamples = [];
for (let index = 0; index < 50; index += 1) {
  const started = performance.now();
  const valid = await groth16.verify(
    verificationKey,
    latestProof.publicSignals,
    latestProof.proof,
  );
  if (!valid) throw new Error("Benchmark proof failed verification");
  verificationSamples.push(performance.now() - started);
}

const requestPayload = JSON.stringify({
  proof: latestProof.proof,
  publicSignals: latestProof.publicSignals,
});
const proofOnly = JSON.stringify(latestProof.proof);
const [wasmStats, zkeyStats] = await Promise.all([stat(wasmPath), stat(zkeyPath)]);
const subprocessSamples = [];
const backendDirectory = resolve(circuitDirectory, "../backend");
for (let index = 0; index < 10; index += 1) {
  const started = performance.now();
  const result = spawnSync(
    process.execPath,
    [resolve(backendDirectory, "verify.mjs"), resolve(backendDirectory, "zk/verification_key.json")],
    { cwd: backendDirectory, input: requestPayload, encoding: "utf8" },
  );
  if (result.status !== 0 || JSON.parse(result.stdout).valid !== true) {
    throw new Error(result.stderr || "Subprocess verifier benchmark failed");
  }
  subprocessSamples.push(performance.now() - started);
}

console.log(JSON.stringify({
  environment: "Node.js reference run; not a mobile-browser claim",
  samples: { proving: provingSamples.length, warmVerification: verificationSamples.length },
  proverMs: {
    median: round(percentile(provingSamples, 0.5)),
    p95: round(percentile(provingSamples, 0.95)),
  },
  warmVerifierMs: {
    median: round(percentile(verificationSamples, 0.5)),
    p95: round(percentile(verificationSamples, 0.95)),
  },
  currentSubprocessVerifierMs: {
    median: round(percentile(subprocessSamples, 0.5)),
    p95: round(percentile(subprocessSamples, 0.95)),
  },
  wireBytes: {
    proofJson: Buffer.byteLength(proofOnly),
    fullRequestJson: Buffer.byteLength(requestPayload),
  },
  staticArtifactBytes: {
    wasm: wasmStats.size,
    provingKey: zkeyStats.size,
  },
}, null, 2));

// SnarkJS workers can retain event-loop handles after the benchmark is done.
process.exit(0);
