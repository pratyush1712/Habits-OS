import type { Metadata } from "next";

import "./globals.css";
import { mono } from "./fonts";

export const metadata: Metadata = {
  title: {
    default: "HabitOS Admin",
    template: "%s | HabitOS Admin",
  },
  description:
    "A private operational surface for inspecting, recomputing, rendering, and syncing HabitOS data.",
  robots: {
    index: false,
    follow: false,
  },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className={mono.variable}>
      <body>{children}</body>
    </html>
  );
}
