"use client";

import { useEffect } from "react";

import { Page } from "@/components/primitives/page";
import { Button } from "@/components/ui/button";

/**
 * Route-level fallback for unexpected admin surface failures.
 */
export default function GlobalError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    console.error(error);
  }, [error]);

  return (
    <div className="min-h-screen bg-paper py-16">
      <Page>
        <div className="mx-auto max-w-[760px] space-y-6">
          <p className="mono-label m-0">Application error</p>
          <h1 className="m-0 text-[clamp(2.5rem,6vw,5rem)] leading-[0.98] tracking-[-0.03em] font-light">
            The admin surface hit an unexpected failure.
          </h1>
          <p className="section-lede m-0">
            Nothing was hidden. The current route failed while rendering or
            loading data.
          </p>
          <div className="paper-panel-inset p-5">
            <p className="m-0 font-mono text-[13px] text-ink-mid">
              {error.message}
            </p>
          </div>
          <Button className="focus-ring" onClick={reset} type="button">
            Retry
          </Button>
        </div>
      </Page>
    </div>
  );
}
