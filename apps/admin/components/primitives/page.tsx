import type { ReactNode } from "react";

import { cn } from "@/lib/utils";

import { Rule } from "./rule";

/**
 * Top-level page wrapper that applies the shared gutter and maximum width.
 */
export function Page({
  children,
  className,
}: {
  children: ReactNode;
  className?: string;
}) {
  return (
    <div className={cn("mx-auto max-w-[1180px] px-[clamp(20px,5vw,88px)]", className)}>
      {children}
    </div>
  );
}

/**
 * Narrow or wide content column depending on reading mode.
 */
export function Column({
  children,
  className,
  wide = false,
}: {
  children: ReactNode;
  className?: string;
  wide?: boolean;
}) {
  return (
    <div className={cn(wide ? "data-column" : "body-column", className)}>
      {children}
    </div>
  );
}

/**
 * Screen section with the numbering and typography from the handoff.
 */
export function Section({
  children,
  kicker,
  lede,
  number,
  title,
}: {
  children: ReactNode;
  kicker: string;
  lede?: ReactNode;
  number: string;
  title: ReactNode;
}) {
  return (
    <section className="border-t border-rule pt-[88px] pb-14 first:border-t-0">
      <div className="grid items-baseline gap-6 md:grid-cols-[88px_1fr]">
        <div className="mono-label flex w-[60px] border-t border-ink pt-3">
          {number}
        </div>
        <div className="space-y-2">
          <p className="mono-label">{kicker}</p>
          <h2 className="section-title m-0">{title}</h2>
        </div>
      </div>
      {lede ? (
        <p className="section-lede mt-4 ml-0 md:ml-[112px]">{lede}</p>
      ) : null}
      <div className="mt-10 ml-0 md:ml-[112px]">{children}</div>
    </section>
  );
}

/**
 * Shared header for private app pages.
 */
export function PageHeader({
  actions,
  eyebrow,
  subtitle,
  title,
}: {
  actions?: ReactNode;
  eyebrow: string;
  subtitle?: ReactNode;
  title: ReactNode;
}) {
  return (
    <header className="space-y-4">
      <div className="flex flex-col gap-4 md:flex-row md:items-end md:justify-between">
        <div className="space-y-2">
          <p className="mono-label">{eyebrow}</p>
          <h1 className="m-0 text-[clamp(2rem,4vw,3.5rem)] leading-[1.02] tracking-[-0.02em] font-light">
            {title}
          </h1>
          {subtitle ? (
            <p className="body-column m-0 text-ink-mid italic">{subtitle}</p>
          ) : null}
        </div>
        {actions ? <div className="flex flex-wrap gap-3">{actions}</div> : null}
      </div>
      <Rule />
    </header>
  );
}
