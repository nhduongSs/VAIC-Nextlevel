import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";

const inter = Inter({ subsets: ["latin", "vietnamese"] });

export const metadata: Metadata = {
  title: "SHB Chat — Tư vấn tiền gửi",
  description: "Trợ lý RAG tra cứu quy định tiền gửi SHB Bank",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="vi" className="dark">
      <body className={inter.className}>{children}</body>
    </html>
  );
}
