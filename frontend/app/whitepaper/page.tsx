import type { Metadata } from "next";
import { PageHero } from "@/components/PageHero";

export const metadata: Metadata = {
  title: "Technical Whitepaper",
  description: "Qyvox architecture, circuit model, ceremony assumptions, threat analysis, and security limitations.",
};

const threats = [
  ["Constraint under-determination", "A witness satisfies an unintended statement because a signal is insufficiently constrained.", "Double-arrow assignments, circomlib comparator constraints, negative witness tests.", "Formal circuit audit required before production."],
  ["Exact proof replay", "A valid proof payload is submitted more than once.", "SHA-256 proof fingerprint with a unique database constraint.", "Bounded challenge signal is planned for stronger freshness."],
  ["Front-running", "A captured proof is submitted by another authenticated session.", "Proof receipt is associated with the authenticated submitter.", "Current proof is not cryptographically bound to that session."],
  ["Stale policy year", "A proof generated for a previous policy epoch is reused.", "FastAPI requires public currentYear to equal the server UTC year.", "Exact-date policy needs a full calendar circuit."],
  ["Toxic-waste compromise", "Setup secrets are retained and used to forge proofs.", "Development artifacts are explicitly non-production.", "Production requires independently verified MPC contributions."],
  ["False source data", "A user proves a qualifying year that is not theirs.", "Out of scope for the baseline knowledge proof.", "Issuer-signed credential commitment is required for real identity assurance."],
];

export default function WhitepaperPage() {
  return (
    <main className="inner-page">
      <PageHero
        index="WP"
        label="Technical whitepaper / revision 0.1"
        title={<>A verifiable claim<br /><span>without data custody.</span></>}
        intro="The mathematical statement, trust assumptions, ceremony requirements, and unresolved security boundaries behind the Qyvox research prototype."
        meta={["Groth16 / BN254", "Circom 2 / 74 constraints", "Research prototype", "Updated 25 Aug 2026"]}
      />

      <div className="paper-layout section-shell">
        <aside className="paper-toc" aria-label="Whitepaper contents">
          <p>CONTENTS</p>
          <a href="#abstract">01 · Abstract</a><a href="#threat-landscape">02 · Threat landscape</a>
          <a href="#primitives">03 · Primitives & circuit</a><a href="#ceremony">04 · Trust ceremony</a>
          <a href="#threat-model">05 · Threat model</a><a href="#limitations">06 · Security bounds</a>
          <a href="#references">07 · References</a>
        </aside>

        <article className="paper-content">
          <section id="abstract">
            <p className="section-label">01 / ABSTRACT</p>
            <h2>Data minimization as a cryptographic property.</h2>
            <p className="paper-lede">Qyvox is a client-proving, server-verifying age-assurance baseline. A private birth year and a public policy year enter an arithmetic circuit. The output states only whether the difference meets an 18-year threshold.</p>
            <p>The browser constructs the witness and Groth16 proof locally. The server receives the proof and public signals, authenticates the requesting session, rejects stale policy epochs, verifies the proof against a fixed key, and stores a privacy-minimal receipt. The system avoids taking custody of the birth year rather than merely encrypting it after collection.</p>
            <div className="paper-callout"><strong>Claim boundary</strong><p>The baseline proves knowledge of <em>a</em> qualifying birth year. It does not yet prove that the witness came from a trusted government or institutional issuer.</p></div>
          </section>

          <section id="threat-landscape">
            <p className="section-label">02 / THREAT LANDSCAPE</p><h2>Centralized assurance externalizes permanent risk.</h2>
            <p>Conventional identity gates concentrate names, dates of birth, document imagery, and addresses into reusable records. Encryption reduces exposure at rest but does not eliminate collection, operational access, retention, deletion, breach notification, or insider-risk obligations.</p>
            <div className="paper-statements">
              <article><span>COLLECTION</span><h3>Every copied field becomes an asset to defend.</h3><p>Security responsibility persists long after the eligibility decision is made.</p></article>
              <article><span>CORRELATION</span><h3>Stable identity records link activity across systems.</h3><p>Data minimization limits the material available for secondary use and compromise.</p></article>
            </div>
          </section>

          <section id="primitives">
            <p className="section-label">03 / PRIMITIVES & CIRCUIT DESIGN</p><h2>Business policy compiled into field constraints.</h2>
            <p>Qyvox uses Groth16 over the BN254 curve because it produces a succinct, non-interactive proof with a small verification workload. Circom compiles the policy into a Rank-1 Constraint System where each constraint is represented as a relation of linear combinations:</p>
            <div className="equation" aria-label="R1CS equation"><span>⟨A, w⟩</span><i>×</i><span>⟨B, w⟩</span><i>=</i><span>⟨C, w⟩</span></div>
            <div className="signal-topology">
              <article><span>PRIVATE WITNESS</span><strong>birthYear</strong><p>Exists inside the local witness calculation and is omitted from the request.</p></article>
              <article><span>PUBLIC INPUT</span><strong>currentYear</strong><p>Binds the proof to the verifier&apos;s current policy epoch.</p></article>
              <article><span>PUBLIC OUTPUT</span><strong>isEligible = 1</strong><p>Communicates only satisfaction of the threshold statement.</p></article>
            </div>
            <pre className="paper-code"><code>{`component ageThreshold = GreaterEqThan(16);
ageThreshold.in[0] <== currentYear - birthYear;
ageThreshold.in[1] <== 18;
isEligible <== ageThreshold.out;

component main { public [currentYear] } = AgeCheck();`}</code></pre>
            <p>The compiled circuit currently contains 74 constraints, 72 wires, one private input, one public input, and one public output. The API additionally requires the output to be exactly one and the public year to match server UTC time.</p>
          </section>

          <section id="ceremony">
            <p className="section-label">04 / TRUST MODEL & CEREMONY</p><h2>A trusted setup must be publicly auditable.</h2>
            <p>Groth16 requires a circuit-specific structured reference string. Security depends on at least one honest participant destroying their secret contribution. Qyvox&apos;s included setup script performs a reproducible single-machine development ceremony and must not be represented as production-ready ceremony evidence.</p>
            <ol className="ceremony-steps">
              <li><span>01</span><div><strong>Universal phase</strong><p>Select a publicly verified Powers of Tau transcript sized above the circuit constraint bound.</p></div></li>
              <li><span>02</span><div><strong>Circuit phase</strong><p>Run independent contributions against the exact published R1CS and record transcript hashes.</p></div></li>
              <li><span>03</span><div><strong>Public beacon</strong><p>Apply a delayed, publicly sourced random beacon and publish verification output.</p></div></li>
              <li><span>04</span><div><strong>Artifact binding</strong><p>Publish R1CS, WASM, zkey, verification key, source commit, and reproducible checksums together.</p></div></li>
            </ol>
          </section>

          <section id="threat-model">
            <p className="section-label">05 / THREAT MODEL</p><h2>Controls, residual risk, and roadmap boundaries.</h2>
            <div className="threat-table" role="table" aria-label="Qyvox threat model">
              <div className="threat-row threat-head" role="row"><span>Vector</span><span>Current control</span><span>Residual / next control</span></div>
              {threats.map(([name, attack, control, residual]) => (
                <div className="threat-row" role="row" key={name}><span><strong>{name}</strong><small>{attack}</small></span><span>{control}</span><span>{residual}</span></div>
              ))}
            </div>
          </section>

          <section id="limitations">
            <p className="section-label">06 / SECURITY BOUNDS</p><h2>What Qyvox does—and does not—prove.</h2>
            <ul className="bounds-list">
              <li><strong>Zero knowledge is computational.</strong><span>The proof is designed to reveal no witness information beyond the public statement under the proving system&apos;s assumptions; “mathematically impossible to recover” would be an overclaim.</span></li>
              <li><strong>Calendar-year arithmetic is coarse.</strong><span>Everyone born in the same year is treated alike. Exact day-level eligibility requires additional public date signals and range constraints.</span></li>
              <li><strong>Source authenticity is absent.</strong><span>A production identity engine must prove possession of an issuer-signed credential commitment and support revocation.</span></li>
              <li><strong>Freshness is incomplete.</strong><span>Exact replay is blocked today, but cryptographic session/challenge binding is a required next circuit revision.</span></li>
              <li><strong>Compliance is contextual.</strong><span>Data minimization can reduce exposure; it does not automatically make every deployment compliant with every jurisdiction.</span></li>
            </ul>
          </section>

          <section id="references">
            <p className="section-label">07 / PRIMARY REFERENCES</p><h2>Implementation foundations.</h2>
            <div className="reference-list">
              <a href="https://eprint.iacr.org/2016/260" target="_blank" rel="noreferrer"><span>01</span><div><strong>Jens Groth — On the Size of Pairing-based Non-interactive Arguments</strong><small>IACR ePrint 2016/260</small></div><i>↗</i></a>
              <a href="https://docs.circom.io/circom-language/signals/" target="_blank" rel="noreferrer"><span>02</span><div><strong>Circom 2 — Signals, assignments, public and private inputs</strong><small>Official language documentation</small></div><i>↗</i></a>
              <a href="https://github.com/iden3/snarkjs" target="_blank" rel="noreferrer"><span>03</span><div><strong>iden3 SnarkJS — Groth16 and Powers of Tau workflow</strong><small>Official implementation repository</small></div><i>↗</i></a>
              <a href="https://zfnd.org/conclusion-of-the-powers-of-tau-ceremony/" target="_blank" rel="noreferrer"><span>04</span><div><strong>Zcash Foundation — Powers of Tau ceremony record</strong><small>Public ceremony context and transcript</small></div><i>↗</i></a>
            </div>
          </section>
        </article>
      </div>
    </main>
  );
}
