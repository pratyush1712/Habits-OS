"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

import { cn } from "@/lib/utils";

const NAV_SECTIONS = [
  {
    label: "Overview",
    links: [
      { href: "/dashboard", label: "Dashboard" },
      { href: "/events", label: "Events" },
      { href: "/medication", label: "Medication" },
      { href: "/protein-shake", label: "Protein Shake" },
      { href: "/habits", label: "Habits" },
    ],
  },
  {
    label: "Operations",
    links: [
      { href: "/automation", label: "Automation" },
      { href: "/renders", label: "Renders" },
      { href: "/connections", label: "Connections" },
      { href: "/settings", label: "Settings" },
    ],
  },
];

/**
 * Big-button navigation that matches the medication tracker control-panel style.
 */
export function Sidebar({
  currentMonth,
}: {
  currentMonth: string;
}) {
  const pathname = usePathname();
  const sections = NAV_SECTIONS.map((section) => ({
    ...section,
    links:
      section.label === "Overview"
        ? [
          section.links[0],
          { href: `/month/${currentMonth}`, label: "Current month" },
          ...section.links.slice(1),
        ]
        : section.links,
  }));

  return (
    <nav className="flex max-w-[860px] flex-col gap-3" aria-label="Admin navigation">
      {sections.map((section) => (
        <div className="space-y-2" key={section.label}>
          <p className="m-0 font-mono text-[11px] font-black tracking-[0.14em] text-slate-700 uppercase">
            {section.label}
          </p>
          <ul className="m-0 flex list-none flex-wrap gap-2 p-0">
            {section.links.map((link) => {
              const active =
                pathname === link.href ||
                (link.href !== "/dashboard" && pathname.startsWith(`${link.href}/`));

              return (
                <li key={link.href}>
                  <Link
                    className={cn(
                      "inline-flex min-h-11 items-center border-2 border-slate-950 px-4 py-2 text-sm font-black no-underline transition-colors active:translate-y-0.5",
                      active
                        ? "bg-emerald-400 text-white hover:bg-blue-500"
                        : "bg-yellow-200 text-slate-950 hover:bg-green-300",
                    )}
                    href={link.href}
                  >
                    {link.label}
                  </Link>
                </li>
              );
            })}
          </ul>
        </div>
      ))}
    </nav>
  );
}
