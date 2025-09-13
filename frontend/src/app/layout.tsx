import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";
import { Providers } from "./providers";

const inter = Inter({
  subsets: ["latin"],
  variable: "--font-inter",
});

export const metadata: Metadata = {
  title: "Cloak - Privacy-First Document Redaction",
  description: "Secure document redaction with visual black boxes and natural language customization",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className={inter.variable}>
      <body className="font-inter antialiased bg-white text-gray-900">
        <Providers>
          {children}
        </Providers>
      </body>
    </html>
  );
}
