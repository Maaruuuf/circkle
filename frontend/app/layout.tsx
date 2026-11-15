import type { Metadata, Viewport } from "next";
import { Inter_Tight, Instrument_Serif } from "next/font/google";
import type { ReactNode } from "react";
import { AuthProvider } from "@/components/AuthContext";
import "./globals.css";

const sans = Inter_Tight({ subsets: ["latin"], variable: "--font-sans", display: "swap" });
const serif = Instrument_Serif({
  subsets: ["latin"],
  weight: "400",
  style: ["normal", "italic"],
  variable: "--font-serif",
  display: "swap",
});

export const metadata: Metadata = {
  title: { default: "Circkle", template: "%s · Circkle" },
  description: "Circkle: share moments with the people you follow.",
};

export const viewport: Viewport = {
  width: "device-width",
  initialScale: 1,
  themeColor: [
    { media: "(prefers-color-scheme: light)", color: "#efe9de" },
    { media: "(prefers-color-scheme: dark)", color: "#121110" },
  ],
};

// Runs before first paint, so the page never flashes the wrong theme.
// Saved choice wins; otherwise follow the operating system setting.
const themeScript = `(function(){try{var t=localStorage.getItem('theme');var d=t?t==='dark':window.matchMedia('(prefers-color-scheme: dark)').matches;document.documentElement.classList.toggle('dark',d);}catch(e){}})();`;

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="en" className={`${sans.variable} ${serif.variable}`} suppressHydrationWarning>
      <head>
        <script dangerouslySetInnerHTML={{ __html: themeScript }} />
      </head>
      <body>
        <AuthProvider>{children}</AuthProvider>
      </body>
    </html>
  );
}
