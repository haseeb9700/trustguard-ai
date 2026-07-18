import "bootstrap/dist/css/bootstrap.min.css";
import type { Metadata } from "next";
import { DM_Sans } from "next/font/google";
import "./globals.css";

const dmSans = DM_Sans({
  variable: "--font-dm-sans",
  subsets: ["latin"],
  weight: ["400", "500", "600", "700"],
});

export const metadata: Metadata = {
  title: "TrustGuard AI — Enterprise AI Governance Platform",
  description:
    "Detect hallucinations, verify trusted sources, score AI risk, and create audit-ready governance workflows for enterprise LLM systems.",
  icons: {
    icon: [{ url: "/icon.svg", type: "image/svg+xml" }, { url: "/favicon.ico" }],
  },
  openGraph: {
    title: "TrustGuard AI — Enterprise AI Governance Platform",
    description:
      "Detect hallucinations, verify trusted sources, score AI risk, and create audit-ready governance workflows for enterprise LLM systems.",
    siteName: "TrustGuard AI",
    type: "website",
  },
  twitter: {
    card: "summary",
    title: "TrustGuard AI — Enterprise AI Governance Platform",
    description:
      "Detect hallucinations, verify trusted sources, score AI risk, and create audit-ready governance workflows for enterprise LLM systems.",
  },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className={`${dmSans.variable} h-full antialiased`}>
      <body className="min-h-full flex flex-col">{children}</body>
    </html>
  );
}
