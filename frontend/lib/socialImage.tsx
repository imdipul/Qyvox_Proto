import { ImageResponse } from "next/og";

export const socialImageSize = { width: 1200, height: 630 };

export function createSocialImage() {
  return new ImageResponse(
    <div style={{ width: "100%", height: "100%", display: "flex", position: "relative", overflow: "hidden", color: "#f4eeea", background: "#150d12", fontFamily: "Arial, sans-serif", padding: "68px 74px" }}>
      <div style={{ position: "absolute", inset: 0, borderTop: "9px solid #eda0b5" }} />
      <div style={{ position: "absolute", right: -180, top: -220, width: 660, height: 660, borderRadius: "50%", background: "radial-gradient(circle,#d77f9940,transparent 67%)" }} />
      <div style={{ position: "absolute", inset: 24, border: "1px solid #ffe5ed20" }} />
      <div style={{ display: "flex", flexDirection: "column", width: "100%" }}>
        <div style={{ display: "flex", alignItems: "center", fontSize: 24, fontWeight: 700 }}>
          <div style={{ display: "flex", width: 50, height: 50, alignItems: "center", justifyContent: "center", marginRight: 16, color: "#150d12", background: "#f4eeea" }}>Q</div>
          QYVOX
          <div style={{ marginLeft: "auto", color: "#a78c96", fontSize: 15, letterSpacing: 2 }}>VERIFIABLE IDENTITY ENGINE</div>
        </div>
        <div style={{ display: "flex", flexDirection: "column", marginTop: "auto", fontSize: 88, fontWeight: 560, lineHeight: 0.92, letterSpacing: -6 }}>
          <span>Prove the fact.</span>
          <span style={{ color: "#eda0b5", fontStyle: "italic" }}>Keep the data.</span>
        </div>
        <div style={{ display: "flex", justifyContent: "space-between", marginTop: 44, paddingTop: 22, borderTop: "1px solid #ffe5ed28", color: "#a78c96", fontSize: 17 }}>
          <span>Browser-local proving · Proof-only verification</span><span>Groth16 / Circom / WASM</span>
        </div>
      </div>
    </div>,
    socialImageSize,
  );
}
