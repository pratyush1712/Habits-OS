import Link from "next/link";
import type { ReactNode } from "react";

import { Page } from "@/components/primitives/page";
import { Rule } from "@/components/primitives/rule";

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
    <div className="min-h-screen bg-paper">
      <Page className="grid min-h-screen gap-10 lg:grid-cols-[220px_minmax(0,1fr)]">
        <aside className="border-r border-rule py-8 pr-0 lg:pr-10">
          <div className="space-y-6 lg:sticky lg:top-8">
            <div className="space-y-2">
              <p className="mono-label m-0">HabitOS Admin</p>
              <p className="m-0 text-sm text-ink-mid">
                Inspect the pipeline, not your discipline.
              </p>
            </div>
            <Rule />
            <Sidebar currentMonth={currentMonth} />
          </div>
        </aside>
        <div className="py-8">
          <header className="space-y-4">
            <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
              <div className="space-y-2">
                <p className="mono-label m-0">Private surface</p>
                <div className="flex flex-wrap items-center gap-3 text-sm text-ink-mid">
                  <span>{userEmail}</span>
                  <span className="text-ink-ghost">·</span>
                  <Link className="muted-link" href="/">
                    Public overview
                  </Link>
                </div>
              </div>
              <SignOutButton />
            </div>
            <Rule />
          </header>
          <main className="pt-8">{children}</main>
        </div>
      </Page>
    </div>
  );
}
