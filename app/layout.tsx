import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Human Layer — Decision desk",
  description: "Turn dense documents into decision-ready evidence.",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return <html lang="ko"><body>{children}</body></html>;
}
