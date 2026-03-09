import { render, screen, waitFor, act } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
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

describe("Error recovery", () => {
  beforeEach(() => {
    vi.useFakeTimers({ shouldAdvanceTime: true });
    mockedSubmitChat.mockReset();
    mockedGetJobStatus.mockReset();
    mockedCheckHealth.mockResolvedValue(true);
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it("shows error banner with retry button on network error", async () => {
    const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime });

    mockedSubmitChat.mockRejectedValue(new Error("Network error"));

    render(<SupportForm />);

    await waitFor(() => {
      expect(screen.getByText("Connected")).toBeInTheDocument();
    });

    await user.type(screen.getByLabelText("Name"), "Ali");
    await user.type(screen.getByLabelText("Email"), "ali@test.com");
    await user.type(screen.getByLabelText("Message"), "Help");
    await user.click(screen.getByRole("button", { name: "Send Message" }));

    await waitFor(() => {
      const errors = screen.getAllByText("Network error");
      expect(errors.length).toBeGreaterThanOrEqual(1);
    });

    // Try Again button appears
    expect(screen.getByRole("button", { name: "Try Again" })).toBeInTheDocument();
  });

  it("retries submission when clicking Try Again", async () => {
    const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime });

    // First call fails, second succeeds
    mockedSubmitChat
      .mockRejectedValueOnce(new Error("Network error"))
      .mockResolvedValueOnce({
        job_id: "job-retry",
        status: "processing",
        retry_after: 2,
      });

    mockedGetJobStatus.mockResolvedValueOnce({
      job_id: "job-retry",
      status: "completed",
      response: "Retry success!",
      error: null,
      retry_after: null,
    });

    render(<SupportForm />);

    await waitFor(() => {
      expect(screen.getByText("Connected")).toBeInTheDocument();
    });

    await user.type(screen.getByLabelText("Name"), "Ali");
    await user.type(screen.getByLabelText("Email"), "ali@test.com");
    await user.type(screen.getByLabelText("Message"), "Help me");
    await user.click(screen.getByRole("button", { name: "Send Message" }));

    // Wait for error
    await waitFor(() => {
      expect(screen.getByRole("button", { name: "Try Again" })).toBeInTheDocument();
    });

    // Click retry
    await user.click(screen.getByRole("button", { name: "Try Again" }));

    // Verify submitChat was called again with same data
    expect(mockedSubmitChat).toHaveBeenCalledTimes(2);
    expect(mockedSubmitChat).toHaveBeenLastCalledWith({
      name: "Ali",
      email: "ali@test.com",
      message: "Help me",
      channel: "web",
    });

    // Poll completes
    await act(async () => {
      await vi.advanceTimersByTimeAsync(5000);
    });

    await waitFor(() => {
      expect(screen.getByText("Retry success!")).toBeInTheDocument();
    });
  });

  it("shows timeout message after 5 minutes of polling", async () => {
    const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime });

    mockedSubmitChat.mockResolvedValue({
      job_id: "job-timeout",
      status: "processing",
      retry_after: 2,
    });

    // Always return processing
    mockedGetJobStatus.mockResolvedValue({
      job_id: "job-timeout",
      status: "processing",
      response: null,
      error: null,
      retry_after: 2,
    });

    render(<SupportForm />);

    await waitFor(() => {
      expect(screen.getByText("Connected")).toBeInTheDocument();
    });

    await user.type(screen.getByLabelText("Name"), "Ali");
    await user.type(screen.getByLabelText("Email"), "ali@test.com");
    await user.type(screen.getByLabelText("Message"), "Help");
    await user.click(screen.getByRole("button", { name: "Send Message" }));

    // Advance past 5-minute timeout
    await act(async () => {
      await vi.advanceTimersByTimeAsync(5 * 60 * 1000 + 1000);
    });

    await waitFor(() => {
      const timeoutErrors = screen.getAllByText(/timed out/i);
      expect(timeoutErrors.length).toBeGreaterThanOrEqual(1);
    });
  });

  it("shows error when polling returns failed status", async () => {
    const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime });

    mockedSubmitChat.mockResolvedValue({
      job_id: "job-fail",
      status: "processing",
      retry_after: 2,
    });

    mockedGetJobStatus.mockResolvedValueOnce({
      job_id: "job-fail",
      status: "failed",
      response: null,
      error: "Agent processing failed",
      retry_after: null,
    });

    render(<SupportForm />);

    await waitFor(() => {
      expect(screen.getByText("Connected")).toBeInTheDocument();
    });

    await user.type(screen.getByLabelText("Name"), "Ali");
    await user.type(screen.getByLabelText("Email"), "ali@test.com");
    await user.type(screen.getByLabelText("Message"), "Help");
    await user.click(screen.getByRole("button", { name: "Send Message" }));

    await act(async () => {
      await vi.advanceTimersByTimeAsync(5000);
    });

    await waitFor(() => {
      const errors = screen.getAllByText("Agent processing failed");
      expect(errors.length).toBeGreaterThanOrEqual(1);
    });
  });

  it("disables submit button during 10-second cooldown after success", async () => {
    const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime });

    mockedSubmitChat.mockResolvedValue({
      job_id: "job-cd",
      status: "processing",
      retry_after: 2,
    });

    mockedGetJobStatus.mockResolvedValueOnce({
      job_id: "job-cd",
      status: "completed",
      response: "Done!",
      error: null,
      retry_after: null,
    });

    render(<SupportForm />);

    await waitFor(() => {
      expect(screen.getByText("Connected")).toBeInTheDocument();
    });

    await user.type(screen.getByLabelText("Name"), "Ali");
    await user.type(screen.getByLabelText("Email"), "ali@test.com");
    await user.type(screen.getByLabelText("Message"), "Help");
    await user.click(screen.getByRole("button", { name: "Send Message" }));

    // Complete the polling
    await act(async () => {
      await vi.advanceTimersByTimeAsync(5000);
    });

    await waitFor(() => {
      expect(screen.getByText("Done!")).toBeInTheDocument();
    });

    // Now in follow-up mode — verify cooldown disables the input area
    const textarea = screen.getByLabelText("Support message");
    expect(textarea).toBeDisabled();

    // After 10 seconds, cooldown ends — textarea and button become interactive
    await act(async () => {
      await vi.advanceTimersByTimeAsync(10000);
    });

    await waitFor(() => {
      expect(screen.getByLabelText("Support message")).not.toBeDisabled();
    });
  });

  it("shows network error with retry after polling fails 3 times", async () => {
    const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime });

    mockedSubmitChat.mockResolvedValue({
      job_id: "job-net",
      status: "processing",
      retry_after: 2,
    });

    // All poll calls throw network error
    mockedGetJobStatus.mockRejectedValue(new Error("fetch failed"));

    render(<SupportForm />);

    await waitFor(() => {
      expect(screen.getByText("Connected")).toBeInTheDocument();
    });

    await user.type(screen.getByLabelText("Name"), "Ali");
    await user.type(screen.getByLabelText("Email"), "ali@test.com");
    await user.type(screen.getByLabelText("Message"), "Help");
    await user.click(screen.getByRole("button", { name: "Send Message" }));

    // Advance through 3 network retries (5s each)
    for (let i = 0; i < 3; i++) {
      await act(async () => {
        await vi.advanceTimersByTimeAsync(5000);
      });
    }

    await waitFor(() => {
      const errors = screen.getAllByText(/Network error/i);
      expect(errors.length).toBeGreaterThanOrEqual(1);
    });
  });
});
