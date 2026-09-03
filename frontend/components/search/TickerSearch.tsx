"use client";

import { useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { Search, Loader2 } from "lucide-react";
import { clsx } from "clsx";
import { searchTickers } from "@/lib/api";
import { useDebounce } from "@/hooks/useDebounce";
import type { SearchResultItem } from "@/types/api";

export function TickerSearch({ compact = false, autoFocus = false }: { compact?: boolean; autoFocus?: boolean }) {
  const router = useRouter();
  const [query, setQuery] = useState("");
  const [resultForQuery, setResultForQuery] = useState<{ query: string; results: SearchResultItem[] } | null>(
    null
  );
  const [open, setOpen] = useState(false);
  const [activeIndex, setActiveIndex] = useState(-1);
  const debounced = useDebounce(query, 250);
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const trimmed = debounced.trim();
    if (trimmed.length < 1) return;

    const controller = new AbortController();
    searchTickers(trimmed, controller.signal)
      .then((res) => {
        if (!controller.signal.aborted) setResultForQuery({ query: trimmed, results: res.results });
      })
      .catch(() => {
        if (!controller.signal.aborted) setResultForQuery({ query: trimmed, results: [] });
      });

    return () => controller.abort();
  }, [debounced]);

  const trimmedQuery = query.trim();
  const loading = trimmedQuery.length > 0 && resultForQuery?.query !== trimmedQuery;
  const visibleResults = trimmedQuery.length < 1 || loading ? [] : resultForQuery?.results ?? [];

  useEffect(() => {
    function handleClickOutside(e: MouseEvent) {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) {
        setOpen(false);
      }
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  function goToTicker(symbol: string) {
    setOpen(false);
    setQuery("");
    setResultForQuery(null);
    router.push(`/analysis?ticker=${encodeURIComponent(symbol.toUpperCase())}`);
  }

  function handleKeyDown(e: React.KeyboardEvent<HTMLInputElement>) {
    if (e.key === "Enter") {
      e.preventDefault();
      if (activeIndex >= 0 && visibleResults[activeIndex]) {
        goToTicker(visibleResults[activeIndex].symbol);
      } else if (query.trim()) {
        goToTicker(query.trim());
      }
    } else if (e.key === "ArrowDown") {
      e.preventDefault();
      setActiveIndex((i) => Math.min(i + 1, visibleResults.length - 1));
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      setActiveIndex((i) => Math.max(i - 1, -1));
    } else if (e.key === "Escape") {
      setOpen(false);
    }
  }

  return (
    <div ref={containerRef} className={clsx("relative", compact ? "w-56" : "w-full max-w-xl")}>
      <label htmlFor="ticker-search" className="sr-only">
        Search for a stock ticker
      </label>
      <div className="relative">
        <Search
          size={compact ? 14 : 18}
          className="absolute left-3 top-1/2 -translate-y-1/2 text-text-muted"
          aria-hidden="true"
        />
        <input
          id="ticker-search"
          type="text"
          role="combobox"
          aria-expanded={open}
          aria-controls="ticker-search-results"
          aria-autocomplete="list"
          autoFocus={autoFocus}
          value={query}
          onChange={(e) => {
            setQuery(e.target.value);
            setOpen(true);
            setActiveIndex(-1);
          }}
          onFocus={() => setOpen(true)}
          onKeyDown={handleKeyDown}
          placeholder="Search ticker (e.g. AAPL, MSFT, NVDA)"
          className={clsx(
            "w-full bg-bg-elevated border border-border-strong rounded-md text-text-primary placeholder:text-text-faint",
            "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent focus-visible:border-accent",
            compact ? "pl-8 pr-3 py-1.5 text-sm" : "pl-11 pr-4 py-3 text-base"
          )}
        />
        {loading && (
          <Loader2
            size={14}
            className="absolute right-3 top-1/2 -translate-y-1/2 text-text-muted animate-spin"
            aria-hidden="true"
          />
        )}
      </div>

      {open && trimmedQuery.length > 0 && (
        <ul
          id="ticker-search-results"
          role="listbox"
          className="absolute z-30 mt-1.5 w-full max-h-80 overflow-y-auto rounded-md border border-border-strong bg-bg-elevated shadow-xl"
        >
          {visibleResults.length === 0 && !loading && (
            <li className="px-4 py-3 text-sm text-text-muted">No matches. Press Enter to try “{trimmedQuery.toUpperCase()}” directly.</li>
          )}
          {visibleResults.map((r, i) => (
            <li key={`${r.symbol}-${r.exchange}`} role="option" aria-selected={i === activeIndex}>
              <button
                type="button"
                onMouseDown={(e) => e.preventDefault()}
                onClick={() => goToTicker(r.symbol)}
                className={clsx(
                  "w-full text-left px-4 py-2.5 flex items-center justify-between gap-3 cursor-pointer",
                  i === activeIndex ? "bg-card-hover" : "hover:bg-card-hover"
                )}
              >
                <span className="flex flex-col min-w-0">
                  <span className="font-mono text-sm text-text-primary">{r.symbol}</span>
                  <span className="text-xs text-text-muted truncate">{r.name}</span>
                </span>
                <span className="text-xs text-text-faint shrink-0">{r.exchange}</span>
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
