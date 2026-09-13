"use client";

import { useCallback, useEffect, useRef, useState } from "react";

export function ImmersiveScene() {
  const frameRef = useRef<HTMLIFrameElement>(null);
  const pointerFrame = useRef<number>(0);
  const [ready, setReady] = useState(false);

  const setActivity = useCallback((active: boolean) => {
    const sceneWindow = frameRef.current?.contentWindow;
    if (!sceneWindow) return;
    sceneWindow.postMessage({ type: "dipul-scene-active", active }, "*");
  }, []);

  useEffect(() => {
    const frame = frameRef.current;
    if (!frame) return;
    const readyFrame = window.requestAnimationFrame(() => setReady(true));

    const observer = new IntersectionObserver(
      ([entry]) => setActivity(entry.isIntersecting && !document.hidden),
      { rootMargin: "160px 0px", threshold: 0.01 },
    );
    observer.observe(frame);

    const onVisibility = () => {
      const rect = frame.getBoundingClientRect();
      setActivity(!document.hidden && rect.bottom > -160 && rect.top < window.innerHeight + 160);
    };

    const onPointerMove = (event: PointerEvent) => {
      if (event.pointerType === "touch" || pointerFrame.current) return;
      pointerFrame.current = window.requestAnimationFrame(() => {
        pointerFrame.current = 0;
        const sceneWindow = frame.contentWindow;
        if (!sceneWindow) return;
        sceneWindow.postMessage(
          { type: "qyvox-pointer", clientX: event.clientX, clientY: event.clientY },
          "*",
        );
      });
    };

    document.addEventListener("visibilitychange", onVisibility);
    window.addEventListener("pointermove", onPointerMove, { passive: true });
    window.addEventListener("resize", onVisibility, { passive: true });

    return () => {
      observer.disconnect();
      document.removeEventListener("visibilitychange", onVisibility);
      window.removeEventListener("pointermove", onPointerMove);
      window.removeEventListener("resize", onVisibility);
      if (pointerFrame.current) window.cancelAnimationFrame(pointerFrame.current);
      window.cancelAnimationFrame(readyFrame);
      setActivity(false);
    };
  }, [setActivity]);

  const handleLoad = () => {
    setActivity(true);
    window.requestAnimationFrame(() => setReady(true));
  };

  return (
    <iframe
      ref={frameRef}
      className={`immersive-scene ${ready ? "is-ready" : ""}`}
      src="/effects/qyvox-field.html"
      title="Interactive cryptographic field"
      tabIndex={-1}
      aria-hidden="true"
      sandbox="allow-same-origin allow-scripts"
      onLoad={handleLoad}
    />
  );
}
