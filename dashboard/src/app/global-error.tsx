"use client";

import { useEffect } from "react";

const button = {
  font: "inherit",
  fontSize: 14,
  padding: "8px 14px",
  borderRadius: 8,
  cursor: "pointer",
  border: "1px solid #d9d2bd",
  background: "#fffdf7",
  color: "#1f2d3d",
} as const;

export default function GlobalError({ error, retry }: { error: Error & { digest?: string }; retry: () => void }) {
  useEffect(() => {
    console.error(error);
  }, [error]);

  return (
    <html lang="en">
      <body
        style={{
          margin: 0,
          minHeight: "100vh",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          background: "#f8f5eb",
          color: "#1f2d3d",
          fontFamily: 'ui-sans-serif, -apple-system, "Segoe UI", sans-serif',
        }}
      >
        <title>Meelu</title>
        <div style={{ textAlign: "center", maxWidth: 380, padding: 24 }}>
          <p style={{ fontSize: 18, fontWeight: 600, margin: "0 0 8px" }}>Meelu ran into a problem.</p>
          <p style={{ fontSize: 14, color: "#5b6b7f", margin: "0 0 20px", lineHeight: 1.55 }}>
            Anything running in the background keeps going. Try again, or head home.
          </p>
          <div style={{ display: "flex", gap: 8, justifyContent: "center" }}>
            <button type="button" style={button} onClick={() => window.history.back()}>
              Back
            </button>
            <button type="button" style={button} onClick={() => retry()}>
              Try again
            </button>
            <button
              type="button"
              style={{ ...button, background: "#2563eb", borderColor: "#2563eb", color: "#fff" }}
              // eslint-disable-next-line @next/next/no-location-assign-relative-destination
              onClick={() => window.location.assign("/dashboard")}
            >
              Home
            </button>
          </div>
        </div>
      </body>
    </html>
  );
}
