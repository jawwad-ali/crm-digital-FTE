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

async function submitInitialMessage(user: ReturnType<typeof userEvent.setup>) {
  // Fill and submit initial form
  await user.type(screen.getByLabelText("Name"), "Ali");
  await user.type(screen.getByLabelText("Email"), "ali@test.com");
  await user.type(screen.getByLabelText("Message"), "First question");
  await user.click(screen.getByRole("button", { name: "Send Message" }));

  // Wait for polling to complete
  await act(async () => {
    await vi.advanceTimersByTimeAsync(5000);
  });

  // Wait for agent response to appear
  await waitFor(() => {
    expect(screen.getByText("Agent reply 1")).toBeInTheDocument();
  });
}

describe("Follow-up flow", () => {
  beforeEach(() => {
    vi.useFakeTimers({ shouldAdvanceTime: true });
    mockedCheckHealth.mockResolvedValue(true);

    let callCount = 0;
    mockedSubmitChat.mockImplementation(async () => {
      callCount++;
      return {
        job_id: `job-${callCount}`,
        status: "processing" as const,
        retry_after: 2,
      };
    });

    let pollCount = 0;
    mockedGetJobStatus.mockImplementation(async () => {
      pollCount++;
      return {
        job_id: `job-x`,
        status: "completed" as const,
        response: `Agent reply ${pollCount}`,
        error: null,
        retry_after: null,
      };
    });
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it("hides InitialForm and shows CustomerHeader after first response", async () => {
    const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime });
    render(<SupportForm />);

    await waitFor(() => {
      expect(screen.getByText("Connected")).toBeInTheDocument();
    });

    // InitialForm visible before submit
    expect(screen.getByLabelText("Name")).toBeInTheDocument();
    expect(screen.getByLabelText("Email")).toBeInTheDocument();

    await submitInitialMessage(user);

    // InitialForm gone, CustomerHeader visible
    expect(screen.queryByLabelText("Name")).not.toBeInTheDocument();
    expect(screen.queryByLabelText("Email")).not.toBeInTheDocument();
    expect(screen.getByText("Ali")).toBeInTheDocument();
    expect(screen.getByText("(ali@test.com)")).toBeInTheDocument();
  });

  it("shows message-only input in follow-up mode", async () => {
    const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime });
    render(<SupportForm />);

    await waitFor(() => {
      expect(screen.getByText("Connected")).toBeInTheDocument();
    });

    await submitInitialMessage(user);

    // MessageInput visible (textarea with "Support message" label)
    expect(screen.getByLabelText("Support message")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Send" })).toBeInTheDocument();
  });

  it("submits follow-up reusing stored name/email", async () => {
    const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime });
    render(<SupportForm />);

    await waitFor(() => {
      expect(screen.getByText("Connected")).toBeInTheDocument();
    });

    await submitInitialMessage(user);

    // Type follow-up
    await user.type(screen.getByLabelText("Support message"), "Follow-up question");
    await user.click(screen.getByRole("button", { name: "Send" }));

    // Verify submitChat was called with the same name/email
    expect(mockedSubmitChat).toHaveBeenLastCalledWith({
      name: "Ali",
      email: "ali@test.com",
      message: "Follow-up question",
      channel: "web",
    });
  });

  it("maintains full conversation history across follow-ups", async () => {
    const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime });
    render(<SupportForm />);

    await waitFor(() => {
      expect(screen.getByText("Connected")).toBeInTheDocument();
    });

    // First exchange
    await submitInitialMessage(user);

    expect(screen.getByText("First question")).toBeInTheDocument();
    expect(screen.getByText("Agent reply 1")).toBeInTheDocument();

    // Second exchange (follow-up)
    await user.type(screen.getByLabelText("Support message"), "Second question");
    await user.click(screen.getByRole("button", { name: "Send" }));

    await act(async () => {
      await vi.advanceTimersByTimeAsync(5000);
    });

    await waitFor(() => {
      expect(screen.getByText("Agent reply 2")).toBeInTheDocument();
    });

    // All messages visible in thread
    expect(screen.getByText("First question")).toBeInTheDocument();
    expect(screen.getByText("Agent reply 1")).toBeInTheDocument();
    expect(screen.getByText("Second question")).toBeInTheDocument();
    expect(screen.getByText("Agent reply 2")).toBeInTheDocument();
  });
});
