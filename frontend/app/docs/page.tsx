import type { Metadata } from "next";
import { DeveloperPlayground } from "@/components/DeveloperPlayground";
import { PageHero } from "@/components/PageHero";

export const metadata: Metadata = {
  title: "Developer Hub",
  description: "Qyvox quickstart, architecture, circuit specification, browser prover integration, and REST API reference.",
};

export default function DocsPage() {
  return (
    <main className="inner-page docs-page">
      <PageHero
        index="DX"
        label="Developer hub / integration guide"
        title={<>From zero to a<br /><span>verified proof.</span></>}
        intro="Inspect the exact privacy boundary, generate a real proof in your browser, and integrate the verifier without transporting private witness data."
        meta={["5-minute baseline", "Next.js + SnarkJS", "FastAPI REST", "Supabase receipt"]}
      />

      <div className="docs-layout section-shell">
        <aside className="docs-nav" aria-label="Documentation contents">
          <p>DOCUMENTATION</p><a href="#quickstart">Quickstart</a><a href="#architecture">Architecture</a>
          <a href="#circuit-specification">Circuit specification</a><a href="#client-sdk">Client integration</a>
          <a href="#rest-api">REST API</a><a href="#database">Database strategy</a><a href="#playground">Live playground</a>
        </aside>

        <article className="docs-content">
          <section id="quickstart">
            <p className="section-label">01 / QUICKSTART</p><h2>First verified proof in five bounded steps.</h2>
            <ol className="quickstart-list">
              <li><span>01</span><div><strong>Compile the circuit</strong><pre><code>{"cd circuits\nnpm ci\n./setup.sh"}</code></pre></div></li>
              <li><span>02</span><div><strong>Apply the privacy-minimal schema</strong><p>Run <code>supabase/schema.sql</code> in the project SQL editor and enable Anonymous Sign-Ins.</p></div></li>
              <li><span>03</span><div><strong>Configure local environments</strong><p>Use only the publishable key in Next.js. Keep the service-role credential inside the backend environment.</p></div></li>
              <li><span>04</span><div><strong>Start the verifier</strong><pre><code>{"cd backend\nuvicorn main:app --reload --port 8000"}</code></pre></div></li>
              <li><span>05</span><div><strong>Start the browser prover</strong><pre><code>{"cd frontend\nnpm run dev"}</code></pre></div></li>
            </ol>
          </section>

          <section id="architecture">
            <p className="section-label">02 / ARCHITECTURE OVERVIEW</p><h2>Data flow with an explicit trust boundary.</h2>
            <div className="architecture-map">
              <article><span>BROWSER / TRUSTED FOR PRIVACY</span><strong>birthYear → witness → proof</strong><p>SnarkJS fetches public WASM and proving-key artifacts. The private input remains in local memory.</p></article>
              <i aria-hidden="true">proof + signals →</i>
              <article><span>FASTAPI / TRUSTED FOR POLICY</span><strong>token → epoch → Groth16 verify</strong><p>The API authenticates the session, validates the public statement, verifies the proof, and applies replay controls.</p></article>
              <i aria-hidden="true">receipt →</i>
              <article><span>SUPABASE / MINIMAL PERSISTENCE</span><strong>UUID + timestamp + hash</strong><p>No age, birth year, date of birth, document image, or witness column exists.</p></article>
            </div>
          </section>

          <section id="circuit-specification">
            <p className="section-label">03 / CIRCUIT SPECIFICATION</p><h2>Seventy-four constraints, one private witness.</h2>
            <div className="spec-grid">
              <dl><div><dt>Curve</dt><dd>BN254 / bn128</dd></div><div><dt>Proving system</dt><dd>Groth16</dd></div><div><dt>Constraints</dt><dd>74</dd></div><div><dt>Wires</dt><dd>72</dd></div></dl>
              <dl><div><dt>Private input</dt><dd>birthYear</dd></div><div><dt>Public input</dt><dd>currentYear</dd></div><div><dt>Public output</dt><dd>isEligible</dd></div><div><dt>Threshold</dt><dd>≥ 18</dd></div></dl>
            </div>
            <pre className="docs-code"><code>{`template AgeCheck() {
  signal input birthYear;
  signal input currentYear;
  signal output isEligible;

  component ageThreshold = GreaterEqThan(16);
  ageThreshold.in[0] <== currentYear - birthYear;
  ageThreshold.in[1] <== 18;
  isEligible <== ageThreshold.out;
}`}</code></pre>
            <p className="docs-note"><strong>Audit note:</strong> the public signal order emitted by SnarkJS is <code>[isEligible, currentYear]</code>. Both the client and server reject any other shape or value.</p>
          </section>

          <section id="client-sdk">
            <p className="section-label">04 / CLIENT INTEGRATION</p><h2>A deliberately small prover interface.</h2>
            <p>The current repository exposes an internal typed module. Publishing it as <code>@qyvox/prover</code> is a release milestone, not a package that is claimed to exist today.</p>
            <pre className="docs-code"><code>{`const { proof, publicSignals } = await generateAgeProof({
  birthYear: privateYear,
  currentYear: new Date().getUTCFullYear(),
});

privateYear = 0; // clear before authentication or transport

await fetch("/api/v1/verify", {
  method: "POST",
  headers: { Authorization: "Bearer <access-token>" },
  body: JSON.stringify({ proof, publicSignals }),
});`}</code></pre>
          </section>

          <section id="rest-api">
            <p className="section-label">05 / REST API REFERENCE</p><h2>POST /api/v1/verify</h2>
            <div className="endpoint-line"><span>POST</span><code>/api/v1/verify</code><strong>Bearer session required</strong></div>
            <pre className="docs-code"><code>{`{
  "proof": {
    "pi_a": ["…", "…", "1"],
    "pi_b": [["…", "…"], ["…", "…"], ["1", "0"]],
    "pi_c": ["…", "…", "1"],
    "protocol": "groth16",
    "curve": "bn128"
  },
  "publicSignals": ["1", "2026"]
}`}</code></pre>
            <p className="docs-note"><strong>Successful response:</strong> the API returns a privacy-safe execution receipt with measured policy, replay, Groth16, and database timings. These measurements are produced during the exact request; no private witness or bearer token is echoed.</p>
            <div className="error-table">
              <div><strong>200</strong><span>Proof valid and receipt recorded.</span></div><div><strong>401</strong><span>Missing, expired, or invalid Supabase bearer session.</span></div>
              <div><strong>403</strong><span>False proof, ineligible output, or stale public year.</span></div><div><strong>409</strong><span>Account or exact proof has already been consumed.</span></div>
              <div><strong>413 / 422</strong><span>Oversized or structurally invalid proof request.</span></div><div><strong>502 / 503</strong><span>Persistence or verifier dependency unavailable.</span></div>
            </div>
          </section>

          <section id="database">
            <p className="section-label">06 / DATABASE STRATEGY</p><h2>Persistence without demographic custody.</h2>
            <pre className="docs-code"><code>{`create table public.verified_users (
  user_id uuid primary key references auth.users(id),
  verified_at timestamptz not null,
  proof_hash text not null unique
);

-- Deliberately absent:
-- birth_year, date_of_birth, age, document_image`}</code></pre>
            <p className="docs-note">The service-role backend is the only database writer. Browser roles receive no read or mutation policy for verification receipts.</p>
          </section>

          <section id="playground"><DeveloperPlayground /></section>
        </article>
      </div>
    </main>
  );
}
