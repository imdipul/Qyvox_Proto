import type { Metadata } from "next";
import Link from "next/link";
import { PageHero } from "@/components/PageHero";

export const metadata: Metadata = {
  title: "Enterprise FAQ & Trust Architecture",
  description: "Direct answers about Qyvox privacy, replay protection, infrastructure, compliance boundaries, and enterprise deployment.",
};

const faqs = [
  ["Can Qyvox recover a user's birth year from a proof?", "The proof is designed to reveal only the public eligibility statement and current policy year. Recovering the private witness from a valid Groth16 proof should be computationally infeasible under the proving system's assumptions. Qyvox does not claim information-theoretic secrecy or that the public eligibility result reveals nothing—it reveals exactly that policy fact."],
  ["Does Qyvox require a blockchain, gas fees, tokens, or cryptocurrency?", "No. The baseline runs on standard web infrastructure: WebAssembly and SnarkJS in the browser, a FastAPI verification service, and PostgreSQL persistence. A blockchain is not required for proof generation or verification."],
  ["How are replay attacks prevented today?", "The current API hashes the canonical proof payload and enforces a unique proof fingerprint, blocking exact reuse. It also binds acceptance to the current UTC year and authenticated submitter. Cryptographic nonce, session, and expiry binding are planned for the next circuit revision; the current design should not be described as fully front-running resistant."],
  ["Does Qyvox prove that the birth year is truthful?", "Not yet. The research baseline proves knowledge of a qualifying value, not provenance from a trusted issuer. Production identity assurance requires a signature or commitment from an authorized credential issuer, plus revocation checks."],
  ["What personal data is stored?", "The verification table contains an authenticated user UUID, verification timestamp, and SHA-256 replay fingerprint. It has no date-of-birth, birth-year, age, address, name, or document-image column."],
  ["What happens to the private input in the browser?", "The birth year is passed to the local witness calculator, then both the React state and mutable local reference are cleared immediately after proof generation and again in the final error-cleanup path. JavaScript runtimes do not provide a formal secure-memory erasure guarantee, so Qyvox accurately describes this as prompt lifecycle minimization—not certified memory zeroization."],
  ["Is Groth16's trusted setup a central trust dependency?", "It is a ceremony assumption, not an operator secret that should remain with Qyvox. Production requires an independently verifiable multi-party ceremony where security holds if at least one contributor destroys their secret randomness. The bundled one-machine ceremony is development-only."],
  ["Is Qyvox automatically GDPR, KYC, AML, or fintech compliant?", "No product can truthfully guarantee universal compliance from architecture alone. Data minimization can materially reduce exposure, but lawful basis, notices, retention, user rights, sector rules, issuer trust, and deployment jurisdiction still require legal and operational review."],
  ["Can enterprises self-host the verifier?", "The architecture is designed for it: the verification key and circuit artifacts are portable, and the verifier has no need for raw witness data. Production packaging, key provenance, monitoring, and service-level terms remain part of the commercialization roadmap."],
  ["What fails safely?", "Malformed, oversized, off-curve, stale, ineligible, replayed, and unauthenticated requests are rejected. Verifier runtime failures return service errors rather than being misclassified as invalid proofs, and persistence failure never produces a successful receipt."],
];

export default function FaqPage() {
  return (
    <main className="inner-page faq-page">
      <PageHero
        index="TR"
        label="Enterprise FAQ / trust architecture"
        title={<>Hard questions.<br /><span>Bounded answers.</span></>}
        intro="Security authority comes from stating assumptions, residual risk, and deployment obligations as clearly as the benefits."
        meta={["No blockchain required", "Proof-only API", "Issuer layer planned", "Compliance is contextual"]}
      />

      <section className="faq-layout section-shell">
        <div className="faq-intro"><p className="section-label">01 / DUE DILIGENCE</p><h2>What technical reviewers should ask.</h2><p>Every answer below distinguishes the current research baseline from the controls required for a production identity network.</p></div>
        <div className="faq-list">
          {faqs.map(([question, answer], index) => (
            <details key={question} open={index === 0}>
              <summary><span>{String(index + 1).padStart(2, "0")}</span><strong>{question}</strong></summary>
              <p>{answer}</p>
            </details>
          ))}
        </div>
      </section>

      <section className="trust-principles section-shell">
        <div><p className="section-label">02 / ENTERPRISE TRUST PRINCIPLES</p><h2>Adopt the proof, audit the assumptions.</h2></div>
        <div className="principle-grid">
          <article><span>01</span><h3>Minimize custody</h3><p>Do not collect a sensitive value when the business decision needs only a predicate.</p></article>
          <article><span>02</span><h3>Publish artifacts</h3><p>Bind source, R1CS, proving key, verification key, ceremony transcript, and release checksums.</p></article>
          <article><span>03</span><h3>Fail closed</h3><p>Reject malformed statements, stale epochs, verifier outages, and persistence failures by default.</p></article>
          <article><span>04</span><h3>Separate claims</h3><p>Keep measured results, security assumptions, legal interpretation, and roadmap targets distinct.</p></article>
        </div>
      </section>

      <section className="enterprise-cta faq-cta">
        <p className="eyebrow"><span>03</span> Technical evaluation</p><h2>Review the implementation boundary before the pitch deck.</h2>
        <div><p>Start with the whitepaper, reproduce the benchmark, and exercise the real proof payload.</p><Link className="primary-link" href="/whitepaper">Open whitepaper <span>↗</span></Link><Link className="text-link" href="/docs">Developer hub <span>→</span></Link></div>
      </section>
    </main>
  );
}
