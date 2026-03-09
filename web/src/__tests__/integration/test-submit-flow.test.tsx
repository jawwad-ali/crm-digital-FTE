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

describe("Submit flow integration", () => {
  beforeEach(() => {
    vi.useFakeTimers({ shouldAdvanceTime: true });
    mockedSubmitChat.mockReset();
    mockedGetJobStatus.mockReset();
    mockedCheckHealth.mockResolvedValue(true);
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it("submits form, shows processing, then displays agent response", async () => {
    const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime });

    mockedSubmitChat.mockResolvedValue({
      job_id: "job-123",
      status: "processing",
      retry_after: 2,
    });

    mockedGetJobStatus
      .mockResolvedValueOnce({
        job_id: "job-123",
        status: "processing",
        response: null,
        error: null,
        retry_after: 2,
      })
      .mockResolvedValueOnce({
        job_id: "job-123",
        status: "completed",
        response: "Here is your answer with **bold**",
        error: null,
        retry_after: null,
      });

    render(<SupportForm />);

    // Wait for health check
    await waitFor(() => {
      expect(screen.getByText("Connected")).toBeInTheDocument();
    });

    // Fill form
    await user.type(screen.getByLabelText("Name"), "Ali");
    await user.type(screen.getByLabelText("Email"), "ali@test.com");
    await user.type(screen.getByLabelText("Message"), "How do I reset my password?");
    await user.click(screen.getByRole("button", { name: "Send Message" }));

    // Verify submitChat was called
    expect(mockedSubmitChat).toHaveBeenCalledWith({
      name: "Ali",
      email: "ali@test.com",
      message: "How do I reset my password?",
      channel: "web",
    });

    // Customer message appears
    expect(screen.getByText("How do I reset my password?")).toBeInTheDocument();

    // Processing indicator appears
    await waitFor(() => {
      expect(screen.getByText("Processing your request...")).toBeInTheDocument();
    });

    // First poll — still processing
    await act(async () => {
      await vi.advanceTimersByTimeAsync(5000);
    });

    // Second poll — completed
    await act(async () => {
      await vi.advanceTimersByTimeAsync(2000);
    });

    // Agent response appears
    await waitFor(() => {
      expect(screen.getByText(/Here is your answer/)).toBeInTheDocument();
    });
  });

  it("shows error when submitChat fails", async () => {
    const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime });

    mockedSubmitChat.mockRejectedValue(new Error("Server error"));

    render(<SupportForm />);

    await waitFor(() => {
      expect(screen.getByText("Connected")).toBeInTheDocument();
    });

    await user.type(screen.getByLabelText("Name"), "Ali");
    await user.type(screen.getByLabelText("Email"), "ali@test.com");
    await user.type(screen.getByLabelText("Message"), "Help");
    await user.click(screen.getByRole("button", { name: "Send Message" }));

    // Error appears in StatusIndicator banner and in the ChatMessage
    await waitFor(() => {
      const errors = screen.getAllByText("Server error");
      expect(errors.length).toBeGreaterThanOrEqual(1);
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

    // Poll returns failed
    await act(async () => {
      await vi.advanceTimersByTimeAsync(5000);
    });

    // Error appears in both StatusIndicator and ChatMessage
    await waitFor(() => {
      const errors = screen.getAllByText("Agent processing failed");
      expect(errors.length).toBeGreaterThanOrEqual(1);
    });
  });
});
