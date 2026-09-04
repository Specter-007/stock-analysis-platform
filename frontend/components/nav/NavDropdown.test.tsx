import { describe, expect, it, vi } from "vitest";
import { render, screen, fireEvent, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { NavDropdown } from "@/components/nav/NavDropdown";

vi.mock("next/navigation", () => ({
  usePathname: () => "/markets",
}));

const LINKS = [
  { href: "/markets", label: "Markets" },
  { href: "/backtest", label: "Backtesting" },
];

describe("NavDropdown", () => {
  it("renders the trigger closed by default", () => {
    render(<NavDropdown label="Research" links={LINKS} />);
    expect(screen.getByRole("button", { name: /research/i })).toHaveAttribute("aria-expanded", "false");
    expect(screen.queryByRole("menu")).not.toBeInTheDocument();
  });

  it("opens the menu on click and lists every link as a menuitem", async () => {
    const user = userEvent.setup();
    render(<NavDropdown label="Research" links={LINKS} />);
    await user.click(screen.getByRole("button", { name: /research/i }));

    const menu = screen.getByRole("menu", { name: /research/i });
    const items = within(menu).getAllByRole("menuitem");
    expect(items.map((i) => i.textContent)).toEqual(["Markets", "Backtesting"]);
  });

  it("highlights the trigger when the current route matches a link", async () => {
    const user = userEvent.setup();
    render(<NavDropdown label="Research" links={LINKS} />);
    // pathname mocked to "/markets", which matches the first link
    await user.click(screen.getByRole("button", { name: /research/i }));
    const menu = screen.getByRole("menu");
    const active = within(menu).getByRole("menuitem", { name: "Markets" });
    expect(active.className).toMatch(/font-medium/);
  });

  it("closes when Escape is pressed and returns focus to the trigger", async () => {
    const user = userEvent.setup();
    render(<NavDropdown label="Research" links={LINKS} />);
    const trigger = screen.getByRole("button", { name: /research/i });
    await user.click(trigger);
    expect(screen.getByRole("menu")).toBeInTheDocument();

    fireEvent.keyDown(document, { key: "Escape" });

    expect(screen.queryByRole("menu")).not.toBeInTheDocument();
    expect(trigger).toHaveFocus();
  });

  it("closes when clicking a menu item", async () => {
    const user = userEvent.setup();
    render(<NavDropdown label="Research" links={LINKS} />);
    await user.click(screen.getByRole("button", { name: /research/i }));
    await user.click(screen.getByRole("menuitem", { name: "Backtesting" }));
    expect(screen.queryByRole("menu")).not.toBeInTheDocument();
  });

  it("closes on an outside click", async () => {
    const user = userEvent.setup();
    render(
      <div>
        <div data-testid="outside">outside</div>
        <NavDropdown label="Research" links={LINKS} />
      </div>
    );
    await user.click(screen.getByRole("button", { name: /research/i }));
    expect(screen.getByRole("menu")).toBeInTheDocument();

    await user.click(screen.getByTestId("outside"));
    expect(screen.queryByRole("menu")).not.toBeInTheDocument();
  });
});
