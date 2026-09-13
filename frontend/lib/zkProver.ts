export interface Groth16Proof {
  pi_a: [string, string, string];
  pi_b: [
    [string, string],
    [string, string],
    [string, string],
  ];
  pi_c: [string, string, string];
  protocol: "groth16";
  curve: "bn128";
}

export interface ProofBundle {
  proof: Groth16Proof;
  publicSignals: string[];
}

interface AgeProofInput {
  birthYear: number;
  currentYear: number;
}

const WASM_URL = "/zk/age_check.wasm";
const PROVING_KEY_URL = "/zk/age_check_final.zkey";

/**
 * Generate Qyvox's Groth16 proof entirely inside the browser.
 *
 * Dynamic import keeps SnarkJS and its WebAssembly plumbing out of server-side
 * rendering. fullProve fetches only the public circuit artifacts; it does not
 * make an application API request and never serializes the private birthYear.
 */
export async function generateAgeProof({
  birthYear,
  currentYear,
}: AgeProofInput): Promise<ProofBundle> {
  if (typeof window === "undefined") {
    throw new Error("Age proofs can only be generated in a browser.");
  }
  if (!Number.isSafeInteger(birthYear) || !Number.isSafeInteger(currentYear)) {
    throw new Error("Birth year and current year must be whole numbers.");
  }

  const snarkjs = await import("snarkjs");
  const result = await snarkjs.groth16.fullProve(
    {
      // String inputs avoid accidental floating-point formatting. SnarkJS
      // converts them to finite-field values inside the local witness builder.
      birthYear: birthYear.toString(10),
      currentYear: currentYear.toString(10),
    },
    WASM_URL,
    PROVING_KEY_URL,
  );

  const proof = result.proof as Groth16Proof;
  const publicSignals = result.publicSignals.map(String);

  // Defense in depth: refuse to transmit an unexpected public statement even
  // though the API independently enforces the same values.
  if (
    publicSignals.length !== 2 ||
    publicSignals[0] !== "1" ||
    publicSignals[1] !== currentYear.toString(10)
  ) {
    throw new Error("The prover produced an unexpected public statement.");
  }

  return { proof, publicSignals };
}

