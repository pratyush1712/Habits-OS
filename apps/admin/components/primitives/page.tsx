import type { ReactNode } from "react";

import { cn } from "@/lib/utils";

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
    <div className={cn("mx-auto max-w-[1240px] px-4 sm:px-6 lg:px-8", className)}>
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
 * Bold section block for operational pages.
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
    <section className="mt-6 border-4 border-slate-950 bg-white p-5 first:mt-0 sm:p-6">
      <div className="flex flex-col gap-3 border-b-4 border-slate-950 pb-4 sm:flex-row sm:items-start sm:justify-between">
        <div className="space-y-2">
          <p className="mono-label m-0 text-blue-700">{kicker}</p>
          <h2 className="section-title m-0">{title}</h2>
        </div>
        <div className="inline-flex w-fit border-2 border-slate-950 bg-yellow-300 px-3 py-1 font-mono text-sm font-black">
          {number}
        </div>
      </div>
      {lede ? <p className="section-lede mt-4 mb-0">{lede}</p> : null}
      <div className="mt-5">{children}</div>
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
    <header className="border-4 border-slate-950 bg-white p-5 sm:p-6">
      <div className="flex flex-col gap-4 md:flex-row md:items-end md:justify-between">
        <div className="space-y-3">
          <p className="mono-label m-0 text-blue-700">{eyebrow}</p>
          <h1 className="m-0 text-[clamp(2.5rem,6vw,5rem)] leading-none font-black tracking-[-0.05em]">
            {title}
          </h1>
          {subtitle ? (
            <p className="m-0 max-w-[70ch] text-xl leading-snug font-black text-slate-800">
              {subtitle}
            </p>
          ) : null}
        </div>
        {actions ? <div className="flex flex-wrap gap-3">{actions}</div> : null}
      </div>
    </header>
  );
}
