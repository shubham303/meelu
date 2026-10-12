import { ImageResponse } from "next/og";
import { readFile } from "node:fs/promises";
import { join } from "node:path";
import { site } from "@/lib/site";

export const alt = `${site.name} — ${site.tagline}`;
export const size = { width: 1200, height: 630 };
export const contentType = "image/png";

// The @4x lockup carries the real Fraunces wordmark as outlines, so the card
// stays on-brand without shipping a font to the image renderer.
const lockup = await readFile(
  join(process.cwd(), "public", "meelu-logo.png"),
).then((file) => `data:image/png;base64,${file.toString("base64")}`);

export default function OpenGraphImage() {
  return new ImageResponse(
    (
      <div
        style={{
          width: "100%",
          height: "100%",
          display: "flex",
          flexDirection: "column",
          justifyContent: "center",
          background: "#f8f5eb",
          padding: "96px 88px",
          borderBottom: "16px solid #2563eb",
        }}
      >
        <img src={lockup} alt="" width={523} height={135} />
        <div
          style={{
            display: "flex",
            marginTop: 64,
            fontSize: 58,
            lineHeight: 1.15,
            letterSpacing: "-0.02em",
            color: "#1f2d3d",
          }}
        >
          {site.tagline}
        </div>
      </div>
    ),
    size,
  );
}
