import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";
import { Header } from "@/components/layout/Header";

const inter = Inter({ subsets: ["latin"] });

export const metadata: Metadata = {
  title: "BizSkill AI - Learn Business Skills in Bite-Sized Videos",
  description:
    "AI-powered video learning platform for busy professionals. Get actionable business insights from top YouTube content.",
  keywords: [
    "business skills",
    "professional development",
    "micro-learning",
    "video learning",
    "leadership",
    "productivity",
  ],
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body className={inter.className}>
        <Header />
        <main className="min-h-screen">{children}</main>
      </body>
    </html>
  );
}
