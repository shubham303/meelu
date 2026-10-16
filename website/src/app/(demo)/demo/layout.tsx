import type { Metadata } from "next";
import "./demo.css";
import { DemoBoot } from "./demo-boot";

export const metadata: Metadata = {
  title: "Interactive demo",
  robots: { index: false, follow: false },
};

export default function DemoLayout({ children }: { children: React.ReactNode }) {
  return (
    <DemoBoot>
      {children}
    </DemoBoot>
  );
}
