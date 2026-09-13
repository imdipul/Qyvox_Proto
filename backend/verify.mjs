import { readFile } from "node:fs/promises";
import { exit, stdin, stdout, stderr } from "node:process";
import { groth16 } from "snarkjs";

/** Read a bounded JSON request from Python over stdin. */
async function readStdin(maxBytes = 32_768) {
  const chunks = [];
  let byteLength = 0;

  for await (const chunk of stdin) {
    byteLength += chunk.length;
    if (byteLength > maxBytes) {
      throw new Error("Verifier input exceeded the configured safety limit.");
    }
    chunks.push(chunk);
  }

  return Buffer.concat(chunks).toString("utf8");
}

async function main() {
  const verificationKeyPath = process.argv[2];
  if (!verificationKeyPath) {
    throw new Error("A verification-key path is required.");
  }

  const [verificationKeyText, requestText] = await Promise.all([
    readFile(verificationKeyPath, "utf8"),
    readStdin(),
  ]);

  const verificationKey = JSON.parse(verificationKeyText);
  const request = JSON.parse(requestText);

  let valid = false;
  try {
    valid = await groth16.verify(
      verificationKey,
      request.publicSignals,
      request.proof,
    );
  } catch {
    // Structurally valid JSON can still contain off-curve or out-of-field
    // points. Those are an invalid proof (HTTP 403), not a verifier outage.
    valid = false;
  }

  // stdout is a machine-readable channel consumed by FastAPI. Diagnostics go
  // to stderr so a dependency log line can never be mistaken for a verdict.
  stdout.write(JSON.stringify({ valid }));
}

main().then(
  () => exit(0),
  (error) => {
    const message = error instanceof Error ? error.message : "Unknown verifier error";
    stderr.write(`${message}\n`);
    exit(1);
  },
);
