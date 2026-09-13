import type { ReactNode } from "react";

export function PageHero({ index, label, title, intro, meta }: {
  index: string;
  label: string;
  title: ReactNode;
  intro: string;
  meta: string[];
}) {
  return (
    <section className="page-hero">
      <div className="page-hero-copy">
        <p className="eyebrow"><span>{index}</span> {label}</p>
        <h1>{title}</h1>
        <p>{intro}</p>
      </div>
      <dl className="page-meta">
        {meta.map((item, itemIndex) => (
          <div key={item}><dt>{String(itemIndex + 1).padStart(2, "0")}</dt><dd>{item}</dd></div>
        ))}
      </dl>
    </section>
  );
}
