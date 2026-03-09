import { render, screen, waitFor, act } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { axe } from "vitest-axe";
import { SupportForm } from "@/components/SupportForm";
import * as api from "@/lib/api";

vi.mock("@/lib/api", () => ({
  submitChat: vi.fn(),
  getJobStatus: vi.fn(),
  checkHealth: vi.fn(),
}));

const mockedSubmitChat = vi.mocked(api.submitChat);
const mockedGetJobStatus = vi.mocked(api.getJobStatus);
const mockedCheckHealth = vi.mocked(api.checkHealth);

describe("Accessibility (axe-core)", () => {
  beforeEach(() => {
    vi.useFakeTimers({ shouldAdvanceTime: true });
    mockedCheckHealth.mockResolvedValue(true);
    mockedSubmitChat.mockResolvedValue({
      job_id: "job-a11y",
      status: "processing",
      retry_after: 2,
    });
    mockedGetJobStatus.mockResolvedValue({
      job_id: "job-a11y",
      status: "completed",
      response: "Agent response",
      error: null,
      retry_after: null,
    });
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it("has no axe violations in initial state", async () => {
    const { container } = render(<SupportForm />);

    await waitFor(() => {
      expect(screen.getByText("Connected")).toBeInTheDocument();
    });

    const results = await axe(container);
    expect(results.violations).toEqual([]);
  });

  it("has no axe violations in follow-up mode", async () => {
    const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime });
    const { container } = render(<SupportForm />);

    await waitFor(() => {
      expect(screen.getByText("Connected")).toBeInTheDocument();
    });

    await user.type(screen.getByLabelText("Name"), "Ali");
    await user.type(screen.getByLabelText("Email"), "ali@test.com");
    await user.type(screen.getByLabelText("Message"), "Hello");
    await user.click(screen.getByRole("button", { name: "Send Message" }));

    await act(async () => {
      await vi.advanceTimersByTimeAsync(5000);
    });

    await waitFor(() => {
      expect(screen.getByText("Agent response")).toBeInTheDocument();
    });

    // Wait for cooldown to expire
    await act(async () => {
      await vi.advanceTimersByTimeAsync(10000);
    });

    const results = await axe(container);
    expect(results.violations).toEqual([]);
  });

  it("has no axe violations in error state", async () => {
    mockedSubmitChat.mockRejectedValue(new Error("Server error"));
    const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime });
    const { container } = render(<SupportForm />);

    await waitFor(() => {
      expect(screen.getByText("Connected")).toBeInTheDocument();
    });

    await user.type(screen.getByLabelText("Name"), "Ali");
    await user.type(screen.getByLabelText("Email"), "ali@test.com");
    await user.type(screen.getByLabelText("Message"), "Help");
    await user.click(screen.getByRole("button", { name: "Send Message" }));

    await waitFor(() => {
      expect(screen.getByRole("button", { name: "Try Again" })).toBeInTheDocument();
    });

    const results = await axe(container);
    expect(results.violations).toEqual([]);
  });
});

describe("Keyboard navigation", () => {
  beforeEach(() => {
    mockedCheckHealth.mockResolvedValue(true);
  });

  it("can tab through all form fields and submit", async () => {
    const user = userEvent.setup();
    render(<SupportForm />);

    await waitFor(() => {
      expect(screen.getByText("Connected")).toBeInTheDocument();
    });

    // Tab to name field
    await user.tab();
    expect(screen.getByLabelText("Name")).toHaveFocus();

    // Tab to email field
    await user.tab();
    expect(screen.getByLabelText("Email")).toHaveFocus();

    // Tab to message field
    await user.tab();
    expect(screen.getByLabelText("Message")).toHaveFocus();

    // Tab to submit button
    await user.tab();
    expect(screen.getByRole("button", { name: "Send Message" })).toHaveFocus();
  });

  it("submits form with Enter key", async () => {
    vi.useFakeTimers({ shouldAdvanceTime: true });
    mockedSubmitChat.mockResolvedValue({
      job_id: "job-kb",
      status: "processing",
      retry_after: 2,
    });

    const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime });
    render(<SupportForm />);

    await waitFor(() => {
      expect(screen.getByText("Connected")).toBeInTheDocument();
    });

    await user.type(screen.getByLabelText("Name"), "Ali");
    await user.type(screen.getByLabelText("Email"), "ali@test.com");
    await user.type(screen.getByLabelText("Message"), "Help");

    // Tab to submit button and press Enter
    await user.tab();
    await user.keyboard("{Enter}");

    expect(mockedSubmitChat).toHaveBeenCalled();

    vi.useRealTimers();
  });
});
