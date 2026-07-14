import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Sheet-to-System Compiler",
  description: "Converte folhas de cálculo críticas em sistemas verificáveis.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="pt-PT">
      <body>{children}</body>
    </html>
  );
}
