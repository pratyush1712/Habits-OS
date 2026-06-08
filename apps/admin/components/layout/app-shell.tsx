import type { ReactNode } from "react";
import Link from "next/link";

import { Page } from "@/components/primitives/page";

import { Sidebar } from "./sidebar";
import { SignOutButton } from "./sign-out-button";

/**
 * Shared private chrome for the authenticated admin surfaces.
 */
export function AppShell({
  children,
  currentMonth,
  userEmail,
}: {
  children: ReactNode;
  currentMonth: string;
  userEmail: string;
}) {
  return (
    <div className="min-h-[100dvh] bg-paper text-slate-950">
      <Page className="py-5 sm:py-7">
        <header className="border-4 border-slate-950 bg-white p-5 sm:p-6">
          <div className="flex flex-col gap-5 xl:flex-row xl:items-start xl:justify-between">
            <div className="space-y-3">
              <p className="mono-label m-0 text-blue-700">HabitOS Admin</p>
              <h1 className="m-0 text-4xl leading-none font-black tracking-tight sm:text-5xl">
                Control panel.
              </h1>
              <div className="flex flex-wrap items-center gap-3 text-base font-black text-slate-800">
                <span>{userEmail}</span>
                <span aria-hidden="true">/</span>
                <Link className="muted-link" href="/">
                  Home
                </Link>
              </div>
            </div>
            <div className="flex flex-col gap-4 xl:items-end">
              <SignOutButton />
              <Sidebar currentMonth={currentMonth} />
            </div>
          </div>
        </header>
        <main className="pt-6">{children}</main>
      </Page>
    </div>
  );
}
