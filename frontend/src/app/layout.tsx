import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "AI Newsroom — Autonomous Editorial Platform",
  description: "LangGraph-powered autonomous newsroom with human editorial approval",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className="dark">
      <body className="min-h-screen bg-[#0a0a0f] text-white antialiased">
        {children}
      </body>
    </html>
  );
}
