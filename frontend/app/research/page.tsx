import type { Metadata } from "next";
import { PageHero } from "@/components/PageHero";

export const metadata: Metadata = {
  title: "Research & Benchmarks",
  description: "Measured Qyvox proving, verification, wire-size, artifact, and architecture performance with explicit methodology.",
};

const benchmarkRows = [
  ["Client / Node reference prover", "34.9 ms median · 270 ms p95", "5 local samples", "Desktop Node reference only; mobile browser campaign remains pending."],
  ["Warm cryptographic verification", "13.0 ms median · 15.3 ms p95", "50 local samples", "Measures Groth16 verification in a warm process."],
  ["Current subprocess verification", "374 ms median · 414 ms p95", "10 local samples", "Includes Node process startup; motivates a persistent verifier service."],
  ["Proof JSON", "724 bytes", "Exact UTF-8 byte length", "SnarkJS object only; not a compressed binary proof."],
  ["Complete request JSON", "763 bytes", "proof + publicSignals", "Actual application body before HTTP framing."],
  ["Static prover artifacts", "79,805 bytes", "WASM + zkey", "38,561-byte WASM and 41,244-byte proving key."],
  ["Circuit size", "74 constraints · 72 wires", "snarkjs r1cs info", "One private input, one public input, one public output."],
  ["Mobile peak memory", "Target: < 65 MB", "Not yet measured", "Must be validated on low-end Android hardware before claiming success."],
];

export default function ResearchPage() {
  return (
    <main className="inner-page research-page">
      <PageHero
        index="RX"
        label="Research / benchmarks / findings"
        title={<>Measure the system.<br /><span>Publish the boundary.</span></>}
        intro="Performance claims are separated into measured reference results, optimization targets, and work that has not yet been validated."
        meta={["Benchmark script included", "74-constraint baseline", "Warm + subprocess paths", "Mobile campaign pending"]}
      />

      <section className="research-summary section-shell">
        <div><p className="section-label">01 / REFERENCE RUN</p><h2>Cryptographic speed is only one layer of latency.</h2></div>
        <p>The current circuit is intentionally tiny. Its warm verifier approaches the sub-15 ms target, while process startup dominates the deployed FastAPI → Node subprocess path. Production optimization should preserve verification isolation without spawning a fresh JavaScript runtime for every request.</p>
      </section>

      <section className="benchmark-table-section section-shell" aria-labelledby="results-title">
        <div className="table-heading"><p className="section-label">02 / RESULTS</p><h2 id="results-title">Measured baseline and open targets.</h2><p>Reference run executed 25 August 2026 using the repository&apos;s generated artifacts. Results are environment-specific and are not mobile-device claims.</p></div>
        <div className="benchmark-table" role="table" aria-label="Qyvox benchmark results">
          <div className="benchmark-row benchmark-head" role="row"><span>Parameter</span><span>Result / target</span><span>Method</span><span>Technical significance</span></div>
          {benchmarkRows.map((row) => <div className="benchmark-row" role="row" key={row[0]}>{row.map((cell) => <span key={cell}>{cell}</span>)}</div>)}
        </div>
      </section>

      <section className="findings-grid section-shell">
        <article>
          <p className="section-label">03 / EDGE COMPUTE</p><h2>Small artifacts change the browser economics.</h2>
          <p>The current WASM and proving key total less than 80 KB, so download size is not the dominant constraint for this baseline. The more important next test is peak memory and worker behavior across Safari and low-end Chromium devices.</p>
          <ul><li>Run 30 cold and warm proofs per device tier.</li><li>Record p50, p95, peak memory, thermal throttling, and failure rate.</li><li>Move proving to a Web Worker before increasing circuit complexity.</li></ul>
        </article>
        <article>
          <p className="section-label">04 / VERIFIER OPTIMIZATION</p><h2>Eliminate process startup, not safety checks.</h2>
          <p>Warm Groth16 verification is roughly 29× faster than the current subprocess median in this reference run. A persistent bounded worker pool or native verifier can recover that gap while retaining payload limits, timeouts, concurrency caps, and off-curve handling.</p>
          <div className="optimization-bars" aria-label="Relative verifier latency"><span><i style={{ width: "100%" }} />Current subprocess · 374 ms</span><span><i style={{ width: "3.5%" }} />Warm crypto core · 13 ms</span></div>
        </article>
        <article>
          <p className="section-label">05 / DATA MINIMIZATION</p><h2>Zero retained DOB changes the compliance surface.</h2>
          <p>Qyvox avoids storing demographic input by design. This can reduce breach impact, subject-access scope, retention complexity, and secondary-use risk—but exact legal consequences remain deployment- and jurisdiction-specific.</p>
          <div className="impact-record"><span>Birth year</span><strong>NOT COLLECTED</strong><span>Document imagery</span><strong>NOT COLLECTED</strong><span>Verification receipt</span><strong>RETAINED</strong></div>
        </article>
      </section>

      <section className="research-roadmap section-shell">
        <div><p className="section-label">06 / VALIDATION ROADMAP</p><h2>Next evidence to produce.</h2></div>
        <ol><li><span>01</span><strong>Mobile matrix</strong><p>Android Go, mid-tier Android, iOS Safari, and desktop browsers.</p></li><li><span>02</span><strong>Persistent verifier</strong><p>Load-test p50/p95/p99 with bounded concurrency and failure injection.</p></li><li><span>03</span><strong>Challenge-bound circuit</strong><p>Add server nonce, session commitment, and expiry to public signals.</p></li><li><span>04</span><strong>Issuer credential</strong><p>Prove age from an issuer-signed commitment with revocation support.</p></li></ol>
      </section>
    </main>
  );
}
