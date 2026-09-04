import { useCallback, useEffect, useRef, useState } from "react";

/**
 * Shared open/close state for a menu/dropdown/popover: closes on Escape,
 * closes on a click outside the container, and returns focus to the
 * trigger element when closed via Escape (so keyboard users don't lose
 * their place). Used by NotificationBell, AccountMenu, and NavDropdown so
 * all three behave identically rather than each re-implementing this.
 */
export function useDismissableMenu<T extends HTMLElement = HTMLDivElement>() {
  const [open, setOpen] = useState(false);
  const containerRef = useRef<T>(null);
  const triggerRef = useRef<HTMLButtonElement>(null);

  const close = useCallback(() => setOpen(false), []);

  useEffect(() => {
    if (!open) return;

    function onClickOutside(e: MouseEvent) {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) {
        setOpen(false);
      }
    }
    function onKeyDown(e: KeyboardEvent) {
      if (e.key === "Escape") {
        setOpen(false);
        triggerRef.current?.focus();
      }
    }

    document.addEventListener("mousedown", onClickOutside);
    document.addEventListener("keydown", onKeyDown);
    return () => {
      document.removeEventListener("mousedown", onClickOutside);
      document.removeEventListener("keydown", onKeyDown);
    };
  }, [open]);

  return { open, setOpen, close, containerRef, triggerRef };
}
