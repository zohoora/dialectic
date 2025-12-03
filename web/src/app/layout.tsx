import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import "./globals.css";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "Case Conference | AI Clinical Deliberation",
  description: "Multi-agent AI system for clinical case deliberation and decision support",
  icons: {
    icon: [
      { url: "/favicon.ico" },
    ],
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
        className={`${geistSans.variable} ${geistMono.variable} antialiased bg-void text-slate-200 min-h-screen`}
      >
        {/* Background effects */}
        <div className="fixed inset-0 bg-gradient-radial from-void-100 via-void to-void pointer-events-none" />
        <div className="fixed inset-0 grid-bg pointer-events-none opacity-50" />
        <div className="fixed top-0 left-1/2 -translate-x-1/2 w-[800px] h-[600px] bg-glow-cyan pointer-events-none opacity-30" />
        <div className="fixed bottom-0 right-0 w-[600px] h-[600px] bg-glow-purple pointer-events-none opacity-20" />
        
        {/* Main content */}
        <div className="relative z-10">
          {children}
        </div>
      </body>
    </html>
  );
}
