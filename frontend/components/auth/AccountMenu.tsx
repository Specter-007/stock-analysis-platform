"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { LogOut, Settings, User as UserIcon } from "lucide-react";
import { useAuth } from "@/lib/auth-context";
import { useDismissableMenu } from "@/hooks/useDismissableMenu";

export function AccountMenu() {
  const { user, loading, logout } = useAuth();
  const router = useRouter();
  const { open, setOpen, close, containerRef, triggerRef } = useDismissableMenu<HTMLDivElement>();

  if (loading) return <div className="w-16 h-8" aria-hidden="true" />;

  if (!user) {
    return (
      <div className="flex items-center gap-1 sm:gap-2">
        <Link href="/login" className="text-sm text-text-muted hover:text-text-primary px-2 py-1.5 whitespace-nowrap">
          Sign in
        </Link>
        {/* Collapsed below `sm` to keep the header from cramming two auth
            actions into the smallest phone widths - reachable from the
            mobile nav panel and from the login page's own "Create an
            account" link there instead. */}
        <Link
          href="/register"
          className="hidden sm:inline-block text-sm bg-accent text-white px-3 py-1.5 rounded-md font-medium hover:opacity-90 whitespace-nowrap"
        >
          Sign up
        </Link>
      </div>
    );
  }

  async function handleLogout() {
    close();
    await logout();
    router.push("/");
  }

  return (
    <div className="relative" ref={containerRef}>
      <button
        ref={triggerRef}
        onClick={() => setOpen((o) => !o)}
        aria-haspopup="menu"
        aria-expanded={open}
        aria-label="Account menu"
        className="flex items-center gap-2 px-2 py-1.5 rounded-md hover:bg-card-hover cursor-pointer"
      >
        <UserIcon size={16} className="text-text-muted shrink-0" aria-hidden="true" />
        <span className="hidden sm:inline text-sm text-text-primary max-w-[120px] truncate">{user.display_name}</span>
      </button>
      {open && (
        <div role="menu" aria-label="Account" className="absolute right-0 mt-2 w-48 bg-card border border-border rounded-md shadow-lg z-50 py-1">
          <Link
            href="/settings/account"
            role="menuitem"
            onClick={close}
            className="flex items-center gap-2 px-3 py-2 text-sm text-text-secondary hover:bg-card-hover hover:text-text-primary"
          >
            <Settings size={14} aria-hidden="true" /> Settings
          </Link>
          <button
            role="menuitem"
            onClick={handleLogout}
            className="w-full flex items-center gap-2 px-3 py-2 text-sm text-text-secondary hover:bg-card-hover hover:text-text-primary cursor-pointer"
          >
            <LogOut size={14} aria-hidden="true" /> Sign out
          </button>
        </div>
      )}
    </div>
  );
}
