"use client";

import { useEffect } from "react";
import { useRouter, usePathname } from "next/navigation";
import { Loader2 } from "lucide-react";
import { useAuth } from "@/lib/auth-context";

/** Wraps a page's content and gates it behind authentication - redirects to
 * /login?next=<current path> if not signed in. Minimizes flicker by
 * rendering nothing (not a flash of protected content) until the initial
 * /api/auth/me check resolves.
 */
export function RequireAuth({ children }: { children: React.ReactNode }) {
  const { user, loading } = useAuth();
  const router = useRouter();
  const pathname = usePathname();

  useEffect(() => {
    if (!loading && !user) {
      router.replace(`/login?next=${encodeURIComponent(pathname)}`);
    }
  }, [loading, user, router, pathname]);

  if (loading || !user) {
    return (
      <div className="flex items-center justify-center py-24">
        <Loader2 size={24} className="animate-spin text-text-muted" aria-hidden="true" />
      </div>
    );
  }

  return <>{children}</>;
}
