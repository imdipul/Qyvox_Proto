"use client";

import { FormEvent, useMemo, useState } from "react";
import { generateAgeProof, type ProofBundle } from "@/lib/zkProver";
import { verifyProof } from "@/lib/verifyProof";

type PlaygroundStage = "idle" | "proving" | "ready" | "verifying" | "verified" | "error";

export function DeveloperPlayground() {
  const currentYear = useMemo(() => new Date().getUTCFullYear(), []);
  const [birthYear, setBirthYear] = useState("");
  const [bundle, setBundle] = useState<ProofBundle | null>(null);
  const [stage, setStage] = useState<PlaygroundStage>("idle");
  const [message, setMessage] = useState("Generate a proof to inspect its public wire representation.");

  async function generate(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    let privateYear = Number(birthYear);
    if (!Number.isInteger(privateYear) || privateYear < currentYear - 120 || currentYear - privateYear < 18) {
      setStage("error");
      setMessage("Enter a valid qualifying year. It will be cleared after proof generation.");
      setBirthYear("");
      return;
    }

    try {
      setStage("proving");
      setMessage("Running the Circom witness calculator and Groth16 prover locally…");
      const nextBundle = await generateAgeProof({ birthYear: privateYear, currentYear });
      privateYear = 0;
      setBirthYear("");
      setBundle(nextBundle);
      setStage("ready");
      setMessage("Proof ready. The private witness is absent from the JSON below.");
    } catch (error) {
      setStage("error");
      setMessage(error instanceof Error ? error.message : "Proof generation failed.");
    } finally {
      privateYear = 0;
      setBirthYear("");
    }
  }

  async function verify() {
    if (!bundle) return;
    try {
      setStage("verifying");
      setMessage("Submitting exactly proof + publicSignals to POST /verify…");
      await verifyProof(bundle);
      setStage("verified");
      setMessage("Server verdict: valid and recorded.");
    } catch (error) {
      setStage("error");
      setMessage(error instanceof Error ? error.message : "Verification failed.");
    }
  }

  const renderedJson = bundle
    ? JSON.stringify({ proof: bundle.proof, publicSignals: bundle.publicSignals }, null, 2)
    : JSON.stringify({ proof: "Generated locally", publicSignals: ["1", String(currentYear)] }, null, 2);

  return (
    <section className="playground" aria-labelledby="playground-title">
      <div className="playground-head">
        <div><p className="section-label">LIVE DEVELOPER CONSOLE</p><h2 id="playground-title">Inspect the proof boundary.</h2></div>
        <span className={`console-state console-${stage}`}>{stage}</span>
      </div>
      <div className="playground-grid">
        <div className="console-controls">
          <form onSubmit={generate}>
            <label htmlFor="playgroundBirthYear">Private birth year</label>
            <input
              id="playgroundBirthYear"
              type="number"
              inputMode="numeric"
              placeholder="1998"
              value={birthYear}
              onChange={(event) => setBirthYear(event.target.value)}
              disabled={stage === "proving" || stage === "verifying"}
            />
            <small>Local witness · purged after fullProve()</small>
            <button type="submit" disabled={!birthYear || stage === "proving" || stage === "verifying"}>Generate proof <span>→</span></button>
          </form>
          <button className="secondary-console-button" type="button" onClick={verify} disabled={!bundle || stage === "verifying"}>POST /verify <span>↗</span></button>
          <p className={`console-message ${stage === "error" ? "console-error" : ""}`} role="status">{message}</p>
        </div>
        <div className="code-window">
          <div className="code-window-bar"><span /><span /><span /><strong>proof-payload.json</strong></div>
          <pre><code>{renderedJson}</code></pre>
        </div>
      </div>
    </section>
  );
}
