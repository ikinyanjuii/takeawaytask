import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "FeatureIQ | Feature Intelligence",
  description: "AI-assisted product feedback triage and prioritisation"
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return <html lang="en"><body>{children}</body></html>;
}
