import type { Metadata } from "next";
import Navbar from "@/components/layout/Navbar";
import Footer from "@/components/layout/Footer";
import Hero from "@/components/landing/Hero";
import Features from "@/components/landing/Features";
import HowItWorks from "@/components/landing/HowItWorks";
import CTA from "@/components/landing/CTA";

export const metadata: Metadata = {
  title: "AI Interview — Mock Interview Coach | Ace Your Next Interview",
  description:
    "Practice behavioral, technical, and role-based interviews with AI Interview, your AI-powered mock interview coach. Get real-time feedback, adaptive questions, and voice interaction.",
};

export default function LandingPage() {
  return (
    <>
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{
          __html: JSON.stringify({
            "@context": "https://schema.org",
            "@type": "SoftwareApplication",
            name: "AI Interview — Mock Interview Coach",
            applicationCategory: "EducationalApplication",
            description:
              "AI-powered mock interview coach with adaptive difficulty, voice interaction, and real-time coaching feedback.",
            operatingSystem: "Web",
            offers: { "@type": "Offer", price: "0", priceCurrency: "USD" },
          }),
        }}
      />
      <Navbar />
      <main>
        <Hero />
        <Features />
        <HowItWorks />
        <CTA />
      </main>
      <Footer />
    </>
  );
}
