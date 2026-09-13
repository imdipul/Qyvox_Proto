"use client";

import { useEffect } from "react";

export function HomeMotion() {
  useEffect(() => {
    const root = document.documentElement;
    const hero = document.querySelector<HTMLElement>(".executive-hero");
    const verifier = document.querySelector<HTMLElement>(".verifier-stage");
    const proofCard = verifier?.querySelector<HTMLElement>(".proof-card");
    const reducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)");
    const coarsePointer = window.matchMedia("(pointer: coarse)");
    let pointerFrame = 0;
    let scrollFrame = 0;

    root.classList.add("motion-ready");

    const revealNodes = Array.from(document.querySelectorAll<HTMLElement>("[data-reveal]"));
    let observer: IntersectionObserver | null = null;

    if (reducedMotion.matches) {
      revealNodes.forEach((node) => node.classList.add("is-visible"));
    } else {
      observer = new IntersectionObserver(
        (entries) => {
          entries.forEach((entry) => {
            if (!entry.isIntersecting) return;
            (entry.target as HTMLElement).classList.add("is-visible");
            observer?.unobserve(entry.target);
          });
        },
        { rootMargin: "0px 0px -9% 0px", threshold: 0.08 },
      );
      revealNodes.forEach((node) => observer?.observe(node));
    }

    const updatePointer = (event: PointerEvent) => {
      if (!hero || coarsePointer.matches || pointerFrame) return;
      pointerFrame = window.requestAnimationFrame(() => {
        pointerFrame = 0;
        const bounds = hero.getBoundingClientRect();
        const x = Math.max(0, Math.min(100, ((event.clientX - bounds.left) / bounds.width) * 100));
        const y = Math.max(0, Math.min(100, ((event.clientY - bounds.top) / bounds.height) * 100));
        hero.style.setProperty("--pointer-x", `${x}%`);
        hero.style.setProperty("--pointer-y", `${y}%`);

        if (proofCard && verifier) {
          const cardBounds = verifier.getBoundingClientRect();
          const cardX = (event.clientX - cardBounds.left) / cardBounds.width - 0.5;
          const cardY = (event.clientY - cardBounds.top) / cardBounds.height - 0.5;
          const inside =
            event.clientX >= cardBounds.left &&
            event.clientX <= cardBounds.right &&
            event.clientY >= cardBounds.top &&
            event.clientY <= cardBounds.bottom;
          proofCard.style.setProperty("--tilt-x", inside ? `${cardY * -1.8}deg` : "0deg");
          proofCard.style.setProperty("--tilt-y", inside ? `${cardX * 1.8}deg` : "0deg");
        }
      });
    };

    const updateScroll = () => {
      if (!hero || scrollFrame) return;
      scrollFrame = window.requestAnimationFrame(() => {
        scrollFrame = 0;
        const progress = Math.max(0, Math.min(1, window.scrollY / Math.max(hero.offsetHeight, 1)));
        hero.style.setProperty("--hero-scroll", String(progress));
      });
    };

    window.addEventListener("pointermove", updatePointer, { passive: true });
    window.addEventListener("scroll", updateScroll, { passive: true });
    updateScroll();

    return () => {
      root.classList.remove("motion-ready");
      observer?.disconnect();
      window.removeEventListener("pointermove", updatePointer);
      window.removeEventListener("scroll", updateScroll);
      if (pointerFrame) window.cancelAnimationFrame(pointerFrame);
      if (scrollFrame) window.cancelAnimationFrame(scrollFrame);
    };
  }, []);

  return null;
}
