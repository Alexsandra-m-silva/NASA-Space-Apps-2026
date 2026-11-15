import type { Metadata } from "next";
import { Fraunces, Figtree } from "next/font/google";
import { SiteHeader } from "@/components/site-header";
import { NewsletterProvider } from "@/lib/newsletter-context";
import { brand } from "@/data/brand";
import "./globals.css";

const display = Fraunces({
  variable: "--font-display",
  subsets: ["latin"],
});

const sans = Figtree({
  variable: "--font-sans",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: {
    default: `${brand.name} — desertification, cost, and regeneration`,
    template: `%s · ${brand.name}`,
  },
  description: brand.purpose,
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body className={`${display.variable} ${sans.variable} font-sans`}>
        <NewsletterProvider>
          <div className="grain min-h-screen">
            <SiteHeader />
            <main className="relative z-10 pt-[3.75rem]">{children}</main>
          </div>
        </NewsletterProvider>
      </body>
    </html>
  );
}
