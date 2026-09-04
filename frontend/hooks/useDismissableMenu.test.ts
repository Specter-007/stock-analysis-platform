import { describe, expect, it } from "vitest";
import { renderHook, act } from "@testing-library/react";
import { useDismissableMenu } from "@/hooks/useDismissableMenu";

describe("useDismissableMenu", () => {
  it("starts closed", () => {
    const { result } = renderHook(() => useDismissableMenu());
    expect(result.current.open).toBe(false);
  });

  it("closes on Escape and returns focus to the trigger", () => {
    const { result } = renderHook(() => useDismissableMenu());
    const trigger = document.createElement("button");
    document.body.appendChild(trigger);
    act(() => {
      result.current.triggerRef.current = trigger;
      result.current.setOpen(true);
    });
    expect(result.current.open).toBe(true);

    act(() => {
      document.dispatchEvent(new KeyboardEvent("keydown", { key: "Escape" }));
    });

    expect(result.current.open).toBe(false);
    expect(document.activeElement).toBe(trigger);
    document.body.removeChild(trigger);
  });

  it("closes on a click outside the container", () => {
    const { result } = renderHook(() => useDismissableMenu());
    const container = document.createElement("div");
    const outside = document.createElement("div");
    document.body.appendChild(container);
    document.body.appendChild(outside);

    act(() => {
      result.current.containerRef.current = container;
      result.current.setOpen(true);
    });
    expect(result.current.open).toBe(true);

    act(() => {
      outside.dispatchEvent(new MouseEvent("mousedown", { bubbles: true }));
    });

    expect(result.current.open).toBe(false);
    document.body.removeChild(container);
    document.body.removeChild(outside);
  });

  it("does not close on a click inside the container", () => {
    const { result } = renderHook(() => useDismissableMenu());
    const container = document.createElement("div");
    const inside = document.createElement("span");
    container.appendChild(inside);
    document.body.appendChild(container);

    act(() => {
      result.current.containerRef.current = container;
      result.current.setOpen(true);
    });

    act(() => {
      inside.dispatchEvent(new MouseEvent("mousedown", { bubbles: true }));
    });

    expect(result.current.open).toBe(true);
    document.body.removeChild(container);
  });

  it("close() sets open to false", () => {
    const { result } = renderHook(() => useDismissableMenu());
    act(() => result.current.setOpen(true));
    act(() => result.current.close());
    expect(result.current.open).toBe(false);
  });
});
