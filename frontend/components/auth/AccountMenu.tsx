"use client";

import { useEffect, useRef, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { LogOut, Settings, User as UserIcon } from "lucide-react";
import { useAuth } from "@/lib/auth-context";

export function AccountMenu() {
  const { user, loading, logout } = useAuth();
  const router = useRouter();
  const [open, setOpen] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    function onClickOutside(e: MouseEvent) {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) setOpen(false);
    }
    document.addEventListener("mousedown", onClickOutside);
    return () => document.removeEventListener("mousedown", onClickOutside);
  }, []);

  if (loading) return <div className="w-16 h-8" aria-hidden="true" />;

  if (!user) {
    return (
      <div className="flex items-center gap-2">
        <Link href="/login" className="text-sm text-text-muted hover:text-text-primary px-2 py-1.5">
          Sign in
        </Link>
        <Link
          href="/register"
          className="text-sm bg-accent text-white px-3 py-1.5 rounded-md font-medium hover:opacity-90"
        >
          Sign up
        </Link>
      </div>
    );
  }

  async function handleLogout() {
    setOpen(false);
    await logout();
    router.push("/");
  }

  return (
    <div className="relative" ref={containerRef}>
      <button
        onClick={() => setOpen((o) => !o)}
        aria-expanded={open}
        aria-label="Account menu"
        className="flex items-center gap-2 px-2 py-1.5 rounded-md hover:bg-card-hover cursor-pointer"
      >
        <UserIcon size={16} className="text-text-muted" aria-hidden="true" />
        <span className="text-sm text-text-primary max-w-[120px] truncate">{user.display_name}</span>
      </button>
      {open && (
        <div className="absolute right-0 mt-2 w-48 bg-card border border-border rounded-md shadow-lg z-50 py-1">
          <Link
            href="/settings/account"
            onClick={() => setOpen(false)}
            className="flex items-center gap-2 px-3 py-2 text-sm text-text-secondary hover:bg-card-hover hover:text-text-primary"
          >
            <Settings size={14} aria-hidden="true" /> Settings
          </Link>
          <button
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
