import { describe, expect, it, vi, beforeEach } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { AccountMenu } from "@/components/auth/AccountMenu";

const push = vi.fn();
vi.mock("next/navigation", () => ({
  useRouter: () => ({ push }),
}));

const logout = vi.fn().mockResolvedValue(undefined);
let mockAuth: { user: { display_name: string } | null; loading: boolean; logout: () => Promise<void> };

vi.mock("@/lib/auth-context", () => ({
  useAuth: () => mockAuth,
}));

describe("AccountMenu", () => {
  beforeEach(() => {
    push.mockClear();
    logout.mockClear();
  });

  it("shows a loading placeholder while auth state is unresolved", () => {
    mockAuth = { user: null, loading: true, logout };
    render(<AccountMenu />);
    expect(screen.queryByRole("button")).not.toBeInTheDocument();
    expect(screen.queryByText("Sign in")).not.toBeInTheDocument();
  });

  it("shows Sign in and Sign up when logged out", () => {
    mockAuth = { user: null, loading: false, logout };
    render(<AccountMenu />);
    expect(screen.getByRole("link", { name: "Sign in" })).toHaveAttribute("href", "/login");
    expect(screen.getByRole("link", { name: "Sign up" })).toHaveAttribute("href", "/register");
  });

  it("collapses Sign up below the `sm` breakpoint instead of overflowing", () => {
    mockAuth = { user: null, loading: false, logout };
    render(<AccountMenu />);
    expect(screen.getByRole("link", { name: "Sign up" }).className).toMatch(/hidden sm:inline-block/);
  });

  it("shows the account trigger with the user's name when logged in", () => {
    mockAuth = { user: { display_name: "Dana" }, loading: false, logout };
    render(<AccountMenu />);
    expect(screen.getByRole("button", { name: "Account menu" })).toHaveAttribute("aria-haspopup", "menu");
    expect(screen.getByText("Dana")).toBeInTheDocument();
    expect(screen.queryByText("Sign in")).not.toBeInTheDocument();
  });

  it("opens a menu with Settings and Sign out", async () => {
    mockAuth = { user: { display_name: "Dana" }, loading: false, logout };
    const user = userEvent.setup();
    render(<AccountMenu />);
    await user.click(screen.getByRole("button", { name: "Account menu" }));

    const menu = screen.getByRole("menu", { name: "Account" });
    expect(menu).toBeInTheDocument();
    expect(screen.getByRole("menuitem", { name: /settings/i })).toHaveAttribute("href", "/settings/account");
    expect(screen.getByRole("menuitem", { name: /sign out/i })).toBeInTheDocument();
  });

  it("logs out and redirects home when Sign out is clicked", async () => {
    mockAuth = { user: { display_name: "Dana" }, loading: false, logout };
    const user = userEvent.setup();
    render(<AccountMenu />);
    await user.click(screen.getByRole("button", { name: "Account menu" }));
    await user.click(screen.getByRole("menuitem", { name: /sign out/i }));

    expect(logout).toHaveBeenCalled();
    expect(push).toHaveBeenCalledWith("/");
  });

  it("closes on Escape and returns focus to the trigger", async () => {
    mockAuth = { user: { display_name: "Dana" }, loading: false, logout };
    const user = userEvent.setup();
    render(<AccountMenu />);
    const trigger = screen.getByRole("button", { name: "Account menu" });
    await user.click(trigger);
    expect(screen.getByRole("menu")).toBeInTheDocument();

    fireEvent.keyDown(document, { key: "Escape" });

    expect(screen.queryByRole("menu")).not.toBeInTheDocument();
    expect(trigger).toHaveFocus();
  });
});
