import type { ReactNode } from "react";
import { format } from "date-fns";

import { AppShell } from "@/components/layout/app-shell";
import { requireAdminSession } from "@/lib/auth";

/**
 * Server-guarded layout for every authenticated admin route.
 */
export default async function PrivateLayout({
  children,
}: {
  children: ReactNode;
}) {
  const session = await requireAdminSession();
  const currentMonth = format(new Date(), "yyyy-MM");

  return (
    <AppShell currentMonth={currentMonth} userEmail={session.user.email}>
      {children}
    </AppShell>
  );
}
