"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { ChevronDown } from "lucide-react";
import { clsx } from "clsx";
import { useDismissableMenu } from "@/hooks/useDismissableMenu";

export interface NavDropdownLink {
  href: string;
  label: string;
}

interface NavDropdownProps {
  label: string;
  links: NavDropdownLink[];
  /** Right-align the panel instead of left-align (useful near the header's right edge). */
  align?: "left" | "right";
}

/**
 * Grouped-links dropdown used for secondary navigation ("Research ▾" /
 * "Menu ▾") at breakpoints too narrow to show every top-level link inline.
 * Highlights itself as active when the current route matches one of its links,
 * so users aren't left wondering where the current page "went."
 */
export function NavDropdown({ label, links, align = "left" }: NavDropdownProps) {
  const pathname = usePathname();
  const { open, setOpen, close, containerRef, triggerRef } = useDismissableMenu<HTMLDivElement>();
  const hasActiveLink = links.some((l) => pathname === l.href || pathname?.startsWith(l.href + "/"));

  return (
    <div className="relative" ref={containerRef}>
      <button
        ref={triggerRef}
        onClick={() => setOpen((o) => !o)}
        aria-haspopup="menu"
        aria-expanded={open}
        className={clsx(
          "flex items-center gap-1 px-3 py-2 rounded-md text-sm font-medium whitespace-nowrap cursor-pointer",
          hasActiveLink ? "text-text-primary" : "text-text-muted hover:text-text-primary"
        )}
      >
        {label}
        <ChevronDown size={14} aria-hidden="true" className={clsx("transition-transform", open && "rotate-180")} />
      </button>
      {open && (
        <div
          role="menu"
          aria-label={label}
          className={clsx(
            "absolute mt-1 min-w-[180px] bg-card border border-border rounded-md shadow-lg z-50 py-1",
            align === "right" ? "right-0" : "left-0"
          )}
        >
          {links.map((l) => {
            const active = pathname === l.href || pathname?.startsWith(l.href + "/");
            return (
              <Link
                key={l.href}
                href={l.href}
                role="menuitem"
                onClick={close}
                className={clsx(
                  "block px-3 py-2 text-sm hover:bg-card-hover",
                  active ? "text-text-primary font-medium" : "text-text-secondary hover:text-text-primary"
                )}
              >
                {l.label}
              </Link>
            );
          })}
        </div>
      )}
    </div>
  );
}
