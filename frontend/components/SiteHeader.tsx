import Link from "next/link";
import Image from "next/image";

const links = [
  { href: "/whitepaper", label: "Whitepaper" },
  { href: "/docs", label: "Developers" },
  { href: "/research", label: "Research" },
  { href: "/faq", label: "Enterprise FAQ" },
];

export function SiteHeader() {
  return (
    <header className="site-header">
      <Link className="brand" href="/" aria-label="Qyvox home">
        <Image
          className="brand-image"
          src="/brand/qyvox-wordmark-white.png"
          alt="Qyvox"
          width={160}
          height={54}
          loading="eager"
        />
      </Link>
      <p className="header-record">APPLIED CRYPTOGRAPHY · CIRCUIT 001</p>
      <nav className="site-nav" aria-label="Primary navigation">
        {links.map((link) => <Link key={link.href} href={link.href}>{link.label}</Link>)}
        <Link className="nav-action" href="/#verifier">Live demo <span>↗</span></Link>
      </nav>
    </header>
  );
}
