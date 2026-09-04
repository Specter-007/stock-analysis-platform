import { describe, expect, it, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { NotificationBell } from "@/components/notifications/NotificationBell";

const push = vi.fn();
vi.mock("next/navigation", () => ({
  useRouter: () => ({ push }),
}));

let mockUser: { id: string } | null = null;
vi.mock("@/lib/auth-context", () => ({
  useAuth: () => ({ user: mockUser }),
}));

const listNotifications = vi.fn();
const markNotificationRead = vi.fn().mockResolvedValue(undefined);
const markAllNotificationsRead = vi.fn().mockResolvedValue(undefined);
const getUnreadNotificationCount = vi.fn().mockResolvedValue({ unread_count: 0 });

vi.mock("@/lib/api", () => ({
  listNotifications: (...args: unknown[]) => listNotifications(...args),
  markNotificationRead: (...args: unknown[]) => markNotificationRead(...args),
  markAllNotificationsRead: (...args: unknown[]) => markAllNotificationsRead(...args),
  getUnreadNotificationCount: (...args: unknown[]) => getUnreadNotificationCount(...args),
}));

describe("NotificationBell", () => {
  beforeEach(() => {
    push.mockClear();
    listNotifications.mockReset().mockResolvedValue({
      unread_count: 1,
      notifications: [
        { id: "n1", title: "Experiment finished", message: "Run #4 completed", read_at: null, created_at: new Date().toISOString(), target_route: "/experiments/4" },
      ],
    });
    markNotificationRead.mockClear();
    markAllNotificationsRead.mockClear();
    getUnreadNotificationCount.mockClear().mockResolvedValue({ unread_count: 1 });
  });

  it("renders nothing when logged out", () => {
    mockUser = null;
    const { container } = render(<NotificationBell />);
    expect(container).toBeEmptyDOMElement();
  });

  it("shows an unread badge for a logged-in user", async () => {
    mockUser = { id: "u1" };
    render(<NotificationBell />);
    await waitFor(() => expect(getUnreadNotificationCount).toHaveBeenCalled());
    expect(await screen.findByText("1")).toBeInTheDocument();
  });

  it("opens the panel and lists notifications on click", async () => {
    mockUser = { id: "u1" };
    const user = userEvent.setup();
    render(<NotificationBell />);
    await user.click(screen.getByRole("button", { name: /notifications/i }));

    expect(await screen.findByText("Experiment finished")).toBeInTheDocument();
    expect(screen.getByRole("menu", { name: "Notifications" })).toBeInTheDocument();
  });

  it("navigates to the target route and marks read on notification click", async () => {
    mockUser = { id: "u1" };
    const user = userEvent.setup();
    render(<NotificationBell />);
    await user.click(screen.getByRole("button", { name: /notifications/i }));
    await user.click(await screen.findByRole("menuitem", { name: /experiment finished/i }));

    expect(markNotificationRead).toHaveBeenCalledWith("n1");
    expect(push).toHaveBeenCalledWith("/experiments/4");
  });

  it("closes on Escape and returns focus to the bell", async () => {
    mockUser = { id: "u1" };
    const user = userEvent.setup();
    render(<NotificationBell />);
    const trigger = screen.getByRole("button", { name: /notifications/i });
    await user.click(trigger);
    expect(await screen.findByRole("menu")).toBeInTheDocument();

    fireEvent.keyDown(document, { key: "Escape" });

    expect(screen.queryByRole("menu")).not.toBeInTheDocument();
    expect(trigger).toHaveFocus();
  });
});
