import type { Metadata } from "next";
import Link from "next/link";
import { ProofDemo } from "@/components/ProofDemo";
import { ImmersiveScene } from "@/components/ImmersiveScene";
import { HomeMotion } from "@/components/HomeMotion";

export const metadata: Metadata = {
  title: "Qyvox — Prove the fact. Keep the data.",
  description: "Zero-knowledge age assurance that verifies eligibility without collecting a birth date or identity document.",
};

const workflow = [
  {
    index: "01",
    title: "Client-side witness",
    label: "PRIVATE INPUT",
    description: "The user enters a birth year into device memory. It is never serialized into an application request.",
    detail: "Memory boundary / browser",
  },
  {
    index: "02",
    title: "WASM ZK prover",
    label: "74 R1CS CONSTRAINTS",
    description: "Circom constraints execute through SnarkJS and WebAssembly. The witness is cleared immediately after fullProve().",
    detail: "Groth16 / BN254",
  },
  {
    index: "03",
    title: "Proof-only attestation",
    label: "PUBLIC VERDICT",
    description: "FastAPI verifies a compact cryptographic statement and persists a UUID, timestamp, and replay fingerprint—never DOB.",
    detail: "Proof + public signals",
  },
];

const assurances = [
  "Raw birth year remains local",
  "Proof-only transport",
  "Independent verifier",
  "No DOB database column",
];

export default function Home() {
  return (
    <main className="home-page">
      <HomeMotion />
      <section className="hero executive-hero" id="top" aria-labelledby="hero-title">
        <ImmersiveScene />
        <div className="hero-copy">
          <p className="eyebrow"><span>01</span> Zero-knowledge age assurance</p>
          <h1 id="hero-title">Prove the fact.<span>Keep the data.</span></h1>
          <p className="hero-intro">
            Qyvox confirms that a user meets an eligibility rule without receiving the sensitive fact behind it. No birthday upload. No identity-document vault. No plaintext honeypot.
          </p>
          <div className="hero-actions">
            <a className="primary-link" href="#verifier">Run the live proof <span>↗</span></a>
            <Link className="text-link" href="/whitepaper">Read the whitepaper <span>→</span></Link>
          </div>
          <dl className="hero-records" aria-label="Qyvox technical record">
            <div><dt>Private data sent</dt><dd>0 bytes</dd></div>
            <div><dt>Current circuit</dt><dd>74 constraints</dd></div>
            <div><dt>Execution</dt><dd>Browser WASM</dd></div>
          </dl>
        </div>
        <ProofDemo />
      </section>

      <section className="signal-strip" aria-label="Technical assurances">
        <div className="signal-track">
          {[0, 1].map((group) => (
            <div className="signal-group" aria-hidden={group === 1} key={group}>
              {assurances.map((assurance) => (
                <span key={assurance}>{assurance}<i aria-hidden="true" /></span>
              ))}
            </div>
          ))}
        </div>
      </section>

      <section className="problem section-shell" aria-labelledby="problem-title">
        <div className="section-heading" data-reveal>
          <p className="eyebrow"><span>02</span> The systemic problem</p>
          <h2 id="problem-title">Identity databases become breach inventories.</h2>
          <p>Conventional verification transfers the most sensitive input to the least controllable part of the system. Qyvox changes the question from “What is your data?” to “Can this claim be proven?”</p>
        </div>
        <div className="comparison-grid">
          <article className="comparison-card comparison-legacy" data-reveal>
            <div className="comparison-top"><span>STANDARD IDENTITY FLOW</span><strong>High custody</strong></div>
            <h3>Collect first.<br />Protect forever.</h3>
            <div className="honeypot-visual" aria-hidden="true">
              <div><span>DOB</span><span>ID PHOTO</span><span>ADDRESS</span><span>NAME</span></div>
              <i>→</i><strong>PLAINTEXT<br />DATABASE</strong>
            </div>
            <ul><li>Persistent breach surface</li><li>Deletion and retention obligations</li><li>Cross-system identity correlation</li></ul>
          </article>
          <article className="comparison-card comparison-qyvox" data-reveal>
            <div className="comparison-top"><span>QYVOX PROOF FLOW</span><strong>Minimal disclosure</strong></div>
            <h3>Prove once.<br />Reveal nothing else.</h3>
            <div className="proof-boundary-visual" aria-hidden="true">
              <div><span>PRIVATE</span><strong>19••</strong></div><i>π</i><div><span>PUBLIC</span><strong>TRUE</strong></div>
            </div>
            <ul><li>Raw input stays on the device</li><li>Server receives a mathematical attestation</li><li>Database stores no birth date or age</li></ul>
          </article>
        </div>
      </section>

      <section className="workflow section-shell" id="how-it-works" aria-labelledby="workflow-title">
        <div className="workflow-heading" data-reveal>
          <p className="eyebrow"><span>03</span> How it works</p>
          <h2 id="workflow-title">Private computation.<br />Public confidence.</h2>
          <p>Three deliberately bounded systems replace one over-privileged identity pipeline.</p>
        </div>
        <div className="workflow-grid">
          {workflow.map((step) => (
            <article key={step.index} data-reveal>
              <div className="workflow-index"><span>{step.index}</span><i /></div>
              <p className="card-index">{step.label}</p>
              <h3>{step.title}</h3>
              <p>{step.description}</p>
              <small>{step.detail}</small>
            </article>
          ))}
        </div>
      </section>

      <section className="benchmarks section-shell" aria-labelledby="benchmark-title">
        <div className="benchmark-copy" data-reveal>
          <p className="eyebrow"><span>04</span> Measured baseline</p>
          <h2 id="benchmark-title">Small circuit.<br />Visible evidence.</h2>
          <p>Reference measurements are published with their boundaries. Mobile performance and a persistent verifier remain explicit validation work—not marketing assumptions.</p>
          <Link className="primary-link" href="/research">Inspect methodology <span>↗</span></Link>
        </div>
        <div className="metric-grid" data-reveal>
          <article><span>01 / WIRE</span><strong>763 B</strong><p>Current complete SnarkJS JSON request, measured.</p></article>
          <article><span>02 / CRYPTO CORE</span><strong>13 ms</strong><p>Warm verification median in the local Node reference run.</p></article>
          <article><span>03 / STATIC KEYS</span><strong>79.8 KB</strong><p>Combined WASM and proving-key artifacts for the 74-constraint circuit.</p></article>
          <article><span>04 / PII AT REST</span><strong>0 B</strong><p>No birth year, age, document image, or witness column exists.</p></article>
        </div>
      </section>

      <section className="enterprise-cta" data-reveal>
        <p className="eyebrow"><span>05</span> Integration surface</p>
        <h2>Reduce identity liability without weakening assurance.</h2>
        <div>
          <p>Review the circuit, threat model, integration contract, and measured constraints before adopting Qyvox.</p>
          <Link className="primary-link" href="/docs">Open developer hub <span>↗</span></Link>
          <Link className="text-link" href="/faq">Enterprise trust FAQ <span>→</span></Link>
        </div>
      </section>
    </main>
  );
}
