import type { Metadata } from "next";
import { Inter } from "next/font/google";
import { Toaster } from "react-hot-toast";
import "./globals.css";

const inter = Inter({ subsets: ["latin"] });

export const metadata: Metadata = {
  title: "SLIME AI - Generative AI Chat",
  description: "SLIME AI is a fluid production-grade chatbot with RAG, memory, and agent tools",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className="dark" suppressHydrationWarning>
      <body className={`${inter.className} bg-gray-950 text-gray-100 antialiased`} suppressHydrationWarning>
        {children}
        <Toaster
          position="top-right"
          toastOptions={{
            style: {
              background: "#07130f",
              color: "#f9fafb",
              border: "1px solid rgba(134, 239, 172, 0.2)",
            },
          }}
        />
      </body>
    </html>
  );
}
