"use client";

import { useEffect, useRef, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { Bell, Loader2 } from "lucide-react";
import { clsx } from "clsx";
import { listNotifications, markNotificationRead, markAllNotificationsRead, getUnreadNotificationCount } from "@/lib/api";
import type { Notification } from "@/types/auth";
import { useAuth } from "@/lib/auth-context";

const POLL_INTERVAL_MS = 30_000;

export function NotificationBell() {
  const { user } = useAuth();
  const router = useRouter();
  const [open, setOpen] = useState(false);
  const [unreadCount, setUnreadCount] = useState(0);
  const [notifications, setNotifications] = useState<Notification[] | null>(null);
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!user) return;
    let cancelled = false;
    async function poll() {
      try {
        const res = await getUnreadNotificationCount();
        if (!cancelled) setUnreadCount(res.unread_count);
      } catch {
        // Silent - a failed poll shouldn't disrupt the rest of the app.
      }
    }
    poll();
    const interval = setInterval(poll, POLL_INTERVAL_MS);
    return () => {
      cancelled = true;
      clearInterval(interval);
    };
  }, [user]);

  useEffect(() => {
    function onClickOutside(e: MouseEvent) {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) setOpen(false);
    }
    document.addEventListener("mousedown", onClickOutside);
    return () => document.removeEventListener("mousedown", onClickOutside);
  }, []);

  async function toggleOpen() {
    const next = !open;
    setOpen(next);
    if (next) {
      const res = await listNotifications();
      setNotifications(res.notifications);
      setUnreadCount(res.unread_count);
    }
  }

  async function handleNotificationClick(n: Notification) {
    if (!n.read_at) {
      await markNotificationRead(n.id);
      setUnreadCount((c) => Math.max(0, c - 1));
      setNotifications((prev) => prev?.map((x) => (x.id === n.id ? { ...x, read_at: new Date().toISOString() } : x)) || null);
    }
    setOpen(false);
    if (n.target_route) router.push(n.target_route);
  }

  async function handleMarkAllRead() {
    await markAllNotificationsRead();
    setUnreadCount(0);
    setNotifications((prev) => prev?.map((x) => ({ ...x, read_at: x.read_at || new Date().toISOString() })) || null);
  }

  if (!user) return null;

  return (
    <div className="relative" ref={containerRef}>
      <button
        onClick={toggleOpen}
        aria-label={`Notifications${unreadCount > 0 ? ` (${unreadCount} unread)` : ""}`}
        aria-expanded={open}
        className="relative p-2 text-text-muted hover:text-text-primary cursor-pointer"
      >
        <Bell size={18} aria-hidden="true" />
        {unreadCount > 0 && (
          <span className="absolute top-1 right-1 min-w-[14px] h-[14px] px-[3px] rounded-full bg-bearish text-white text-[9px] leading-[14px] text-center font-medium">
            {unreadCount > 9 ? "9+" : unreadCount}
          </span>
        )}
      </button>

      {open && (
        <div className="absolute right-0 mt-2 w-80 max-h-96 overflow-y-auto bg-card border border-border rounded-md shadow-lg z-50">
          <div className="flex items-center justify-between px-3 py-2 border-b border-border">
            <span className="text-xs font-semibold text-text-primary uppercase tracking-wide">Notifications</span>
            {unreadCount > 0 && (
              <button onClick={handleMarkAllRead} className="text-xs text-accent hover:underline cursor-pointer">
                Mark all read
              </button>
            )}
          </div>
          {!notifications ? (
            <div className="flex items-center justify-center py-8">
              <Loader2 size={18} className="animate-spin text-text-muted" aria-hidden="true" />
            </div>
          ) : notifications.length === 0 ? (
            <p className="text-xs text-text-muted text-center py-8 px-4">
              No notifications yet. You&apos;ll see updates here when an experiment finishes or a paper-trading
              stop triggers.
            </p>
          ) : (
            <ul className="divide-y divide-border">
              {notifications.map((n) => (
                <li key={n.id}>
                  <button
                    onClick={() => handleNotificationClick(n)}
                    className={clsx(
                      "w-full text-left px-3 py-2.5 hover:bg-card-hover cursor-pointer",
                      !n.read_at && "bg-accent-dim/30"
                    )}
                  >
                    <p className="text-xs font-medium text-text-primary">{n.title}</p>
                    <p className="text-xs text-text-muted mt-0.5 line-clamp-2">{n.message}</p>
                    <p className="text-[10px] text-text-faint mt-1">{new Date(n.created_at).toLocaleString()}</p>
                  </button>
                </li>
              ))}
            </ul>
          )}
          <div className="px-3 py-2 border-t border-border">
            <Link href="/settings/notifications" className="text-xs text-text-muted hover:text-text-primary" onClick={() => setOpen(false)}>
              Notification settings
            </Link>
          </div>
        </div>
      )}
    </div>
  );
}
