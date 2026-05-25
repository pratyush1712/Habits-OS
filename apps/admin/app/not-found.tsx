import Link from "next/link";

import { Page } from "@/components/primitives/page";

/**
 * Not-found surface matching the rest of the editorial shell.
 */
export default function NotFoundPage() {
  return (
    <div className="min-h-screen bg-paper py-16">
      <Page>
        <div className="mx-auto max-w-[760px] space-y-6">
          <p className="mono-label m-0">Not found</p>
          <h1 className="m-0 text-[clamp(2.5rem,6vw,5rem)] leading-[0.98] tracking-[-0.03em] font-light">
            That route is not part of the admin surface.
          </h1>
          <p className="section-lede m-0">
            Use the shell navigation for private routes or return to the public
            overview.
          </p>
          <div className="flex flex-wrap gap-4">
            <Link className="muted-link" href="/dashboard">
              Dashboard
            </Link>
            <Link className="muted-link" href="/">
              Public overview
            </Link>
          </div>
        </div>
      </Page>
    </div>
  );
}
