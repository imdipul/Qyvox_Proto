import Link from "next/link";
import Image from "next/image";
import { SystemStatus } from "@/components/SystemStatus";

export function SiteFooter() {
  return (
    <footer className="portal-footer">
      <div className="footer-lead">
        <Link className="brand footer-brand" href="/">
          <Image
            className="footer-brand-image"
            src="/brand/qyvox-wordmark-white.png"
            alt="Qyvox"
            width={180}
            height={60}
          />
        </Link>
        <p>A zero-knowledge verifiable identity engine for privacy-minimal digital trust.</p>
      </div>
      <div className="footer-column">
        <p>Explore</p>
        <Link href="/whitepaper">Technical whitepaper</Link>
        <Link href="/research">Benchmarks & findings</Link>
        <Link href="/faq">Enterprise trust FAQ</Link>
      </div>
      <div className="footer-column">
        <p>Build</p>
        <Link href="/docs">Developer quickstart</Link>
        <Link href="/docs#circuit-specification">Circuit audit trail</Link>
        <a href="https://github.com/imdipul" target="_blank" rel="noreferrer">GitHub / imdipul ↗</a>
      </div>
      <div className="footer-meta">
        <div><p>Release record</p><span>Research prototype · v0.1</span><span>License model under review</span></div>
        <SystemStatus />
      </div>
      <div className="footer-bottom">
        <span>© {new Date().getUTCFullYear()} Qyvox</span>
        <span>No identity data held at rest</span>
        <Link href="/whitepaper#limitations">Security assumptions & limitations</Link>
      </div>
    </footer>
  );
}
