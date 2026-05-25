"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

import { cn } from "@/lib/utils";

const NAV_SECTIONS = [
  {
    label: "Overview",
    links: [
      { href: "/dashboard", label: "Dashboard", disabled: false },
      { href: "/events", label: "Events", disabled: false },
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
 * Text-first navigation that keeps the design system free of decorative icons.
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
    <nav className="space-y-10">
      {sections.map((section) => (
        <div className="space-y-3" key={section.label}>
          <p className="m-0 text-[12px] italic text-ink-faint">{section.label}</p>
          <ul className="m-0 list-none space-y-1.5 p-0">
            {section.links.map((link) => {
              const active =
                pathname === link.href ||
                (link.href !== "/dashboard" && pathname.startsWith(`${link.href}/`));

              return (
                <li key={link.href}>
                  <Link
                    className={cn(
                      "block no-underline transition-colors",
                      active
                        ? "font-medium italic text-ink"
                        : "text-ink-mid hover:text-ink",
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
