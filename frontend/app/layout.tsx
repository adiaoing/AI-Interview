import type { Metadata } from "next";
import { Geist, Geist_Mono, Syne } from "next/font/google";
import { Analytics } from "@vercel/analytics/react";
import "./globals.css";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

const syne = Syne({
  variable: "--font-brand",
  subsets: ["latin"],
  weight: ["700", "800"],
});

export const metadata: Metadata = {
  title: "AI Interview — Mock Interview Coach | Ace Your Next Interview",
  description:
    "AI Interview is an AI-powered mock interview coach that adapts to your skill level. Practice behavioral, technical, and role-based interviews with real-time feedback and voice interaction.",
  keywords: [
    "AI interview coach",
    "mock interview",
    "interview preparation",
    "behavioral interview practice",
    "technical interview prep",
    "AI interview feedback",
    "job interview practice",
  ],
  openGraph: {
    title: "AI Interview — Mock Interview Coach",
    description:
      "Practice interviews with an AI that adapts to you. Get instant feedback, coaching, and voice-first interaction.",
    type: "website",
    siteName: "AI Interview",
  },
  twitter: {
    card: "summary_large_image",
    title: "AI Interview — Mock Interview Coach",
    description:
      "Practice interviews with an AI that adapts to you. Get instant feedback, coaching, and voice-first interaction.",
  },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className="dark">
      <body
        className={`${geistSans.variable} ${geistMono.variable} ${syne.variable} antialiased bg-black text-white`}
      >
        {children}
        <Analytics />
      </body>
    </html>
  );
}
