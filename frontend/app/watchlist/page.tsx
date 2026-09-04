import WatchlistPageClient from "@/components/watchlist/WatchlistPageClient";
import { RequireAuth } from "@/components/auth/RequireAuth";

export const metadata = {
  title: "Watchlist — Stock Analyst",
};

export default function WatchlistPage() {
  return (
    <RequireAuth>
      <WatchlistPageClient />
    </RequireAuth>
  );
}
