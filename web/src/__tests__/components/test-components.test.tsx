import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import type { Message } from "@/lib/types";
import { InitialForm } from "@/components/InitialForm";
import { ChatMessage } from "@/components/ChatMessage";
import { ChatThread } from "@/components/ChatThread";
import { MessageInput } from "@/components/MessageInput";
import { StatusIndicator } from "@/components/StatusIndicator";
import { MarkdownRenderer } from "@/components/MarkdownRenderer";

// ---------- InitialForm ----------

describe("InitialForm", () => {
  it("renders name, email, and message fields", () => {
    render(<InitialForm onSubmit={vi.fn()} isSubmitting={false} />);

    expect(screen.getByLabelText("Name")).toBeInTheDocument();
    expect(screen.getByLabelText("Email")).toBeInTheDocument();
    expect(screen.getByLabelText("Message")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Send Message" })).toBeInTheDocument();
  });

  it("calls onSubmit with trimmed values on valid submission", async () => {
    const user = userEvent.setup();
    const onSubmit = vi.fn();
    render(<InitialForm onSubmit={onSubmit} isSubmitting={false} />);

    await user.type(screen.getByLabelText("Name"), "  Ali  ");
    await user.type(screen.getByLabelText("Email"), "ali@test.com");
    await user.type(screen.getByLabelText("Message"), "Help me please");
    await user.click(screen.getByRole("button", { name: "Send Message" }));

    expect(onSubmit).toHaveBeenCalledWith("Ali", "ali@test.com", "Help me please");
  });

  it("shows validation errors on empty submit", async () => {
    const user = userEvent.setup();
    render(<InitialForm onSubmit={vi.fn()} isSubmitting={false} />);

    await user.click(screen.getByRole("button", { name: "Send Message" }));

    expect(screen.getByText("Name is required")).toBeInTheDocument();
    expect(screen.getByText("Email is required")).toBeInTheDocument();
    expect(screen.getByText("Message is required")).toBeInTheDocument();
  });

  it("shows invalid email error", async () => {
    const user = userEvent.setup();
    render(<InitialForm onSubmit={vi.fn()} isSubmitting={false} />);

    await user.type(screen.getByLabelText("Name"), "Ali");
    await user.type(screen.getByLabelText("Email"), "not-an-email");
    await user.type(screen.getByLabelText("Message"), "Hello");
    await user.click(screen.getByRole("button", { name: "Send Message" }));

    expect(screen.getByText("Invalid email format")).toBeInTheDocument();
  });

  it("shows Sending... when isSubmitting is true", () => {
    render(<InitialForm onSubmit={vi.fn()} isSubmitting={true} />);
    expect(screen.getByRole("button", { name: "Sending..." })).toBeDisabled();
  });
});

// ---------- ChatMessage ----------

describe("ChatMessage", () => {
  const baseMessage: Message = {
    id: "msg-1",
    role: "customer",
    content: "Hello there",
    timestamp: new Date("2026-03-09T10:30:00"),
    status: "sent",
  };

  it("renders customer message as plain text", () => {
    render(<ChatMessage message={baseMessage} />);
    expect(screen.getByText("Hello there")).toBeInTheDocument();
  });

  it("renders agent message with markdown", () => {
    const agentMsg: Message = {
      ...baseMessage,
      id: "msg-2",
      role: "agent",
      content: "Go to **Settings**",
      status: "completed",
    };
    render(<ChatMessage message={agentMsg} />);
    expect(screen.getByText("Settings")).toBeInTheDocument();
  });

  it("shows pulsing dots for processing status", () => {
    const processingMsg: Message = {
      ...baseMessage,
      status: "processing",
    };
    render(<ChatMessage message={processingMsg} />);
    expect(screen.getByLabelText("Processing")).toBeInTheDocument();
  });

  it("shows error text for failed status", () => {
    const failedMsg: Message = {
      ...baseMessage,
      status: "failed",
      error: "Something went wrong",
    };
    render(<ChatMessage message={failedMsg} />);
    expect(screen.getByText("Something went wrong")).toBeInTheDocument();
  });
});

// ---------- ChatThread ----------

describe("ChatThread", () => {
  it("renders nothing when messages is empty", () => {
    const { container } = render(<ChatThread messages={[]} />);
    expect(container.querySelector('[role="log"]')).not.toBeInTheDocument();
  });

  it("renders messages with log role", () => {
    const messages: Message[] = [
      {
        id: "1",
        role: "customer",
        content: "First message",
        timestamp: new Date(),
        status: "sent",
      },
      {
        id: "2",
        role: "agent",
        content: "Second message",
        timestamp: new Date(),
        status: "completed",
      },
    ];
    render(<ChatThread messages={messages} />);
    expect(screen.getByRole("log")).toBeInTheDocument();
    expect(screen.getByText("First message")).toBeInTheDocument();
    expect(screen.getByText("Second message")).toBeInTheDocument();
  });
});

// ---------- MessageInput ----------

describe("MessageInput", () => {
  it("renders textarea and send button", () => {
    render(<MessageInput onSubmit={vi.fn()} disabled={false} />);
    expect(screen.getByLabelText("Support message")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Send" })).toBeInTheDocument();
  });

  it("shows character counter", () => {
    render(<MessageInput onSubmit={vi.fn()} disabled={false} />);
    expect(screen.getByText("0 / 2000")).toBeInTheDocument();
  });

  it("calls onSubmit on button click and clears input", async () => {
    const user = userEvent.setup();
    const onSubmit = vi.fn();
    render(<MessageInput onSubmit={onSubmit} disabled={false} />);

    await user.type(screen.getByLabelText("Support message"), "Hello");
    await user.click(screen.getByRole("button", { name: "Send" }));

    expect(onSubmit).toHaveBeenCalledWith("Hello");
    expect(screen.getByLabelText("Support message")).toHaveValue("");
  });

  it("submits on Enter (not Shift+Enter)", async () => {
    const user = userEvent.setup();
    const onSubmit = vi.fn();
    render(<MessageInput onSubmit={onSubmit} disabled={false} />);

    const textarea = screen.getByLabelText("Support message");
    await user.type(textarea, "Test message");
    await user.keyboard("{Enter}");

    expect(onSubmit).toHaveBeenCalledWith("Test message");
  });

  it("does not submit on Shift+Enter", async () => {
    const user = userEvent.setup();
    const onSubmit = vi.fn();
    render(<MessageInput onSubmit={onSubmit} disabled={false} />);

    const textarea = screen.getByLabelText("Support message");
    await user.type(textarea, "Test");
    await user.keyboard("{Shift>}{Enter}{/Shift}");

    expect(onSubmit).not.toHaveBeenCalled();
  });

  it("disables when disabled prop is true", () => {
    render(<MessageInput onSubmit={vi.fn()} disabled={true} />);
    expect(screen.getByLabelText("Support message")).toBeDisabled();
  });
});

// ---------- StatusIndicator ----------

describe("StatusIndicator", () => {
  it("shows checking state when isHealthy is null", () => {
    render(
      <StatusIndicator isHealthy={null} isProcessing={false} error={null} />,
    );
    expect(screen.getByText("Checking connection...")).toBeInTheDocument();
  });

  it("shows connected when healthy", () => {
    render(
      <StatusIndicator isHealthy={true} isProcessing={false} error={null} />,
    );
    expect(screen.getByText("Connected")).toBeInTheDocument();
  });

  it("shows unavailable when unhealthy", () => {
    render(
      <StatusIndicator isHealthy={false} isProcessing={false} error={null} />,
    );
    expect(screen.getByText("Service unavailable")).toBeInTheDocument();
  });

  it("shows processing text when isProcessing", () => {
    render(
      <StatusIndicator isHealthy={true} isProcessing={true} error={null} />,
    );
    expect(screen.getByText("Processing your request...")).toBeInTheDocument();
  });

  it("shows error banner with retry button", async () => {
    const user = userEvent.setup();
    const onRetry = vi.fn();
    render(
      <StatusIndicator
        isHealthy={true}
        isProcessing={false}
        error="Something failed"
        onRetry={onRetry}
      />,
    );
    expect(screen.getByText("Something failed")).toBeInTheDocument();
    await user.click(screen.getByText("Try Again"));
    expect(onRetry).toHaveBeenCalled();
  });
});

// ---------- MarkdownRenderer ----------

describe("MarkdownRenderer", () => {
  it("renders bold text", () => {
    render(<MarkdownRenderer content="**bold text**" />);
    const strong = screen.getByText("bold text");
    expect(strong.tagName).toBe("STRONG");
  });

  it("renders unordered lists", () => {
    const md = `- item one
- item two`;
    render(<MarkdownRenderer content={md} />);
    expect(screen.getByText("item one")).toBeInTheDocument();
    expect(screen.getByText("item two")).toBeInTheDocument();
  });

  it("renders links with target _blank", () => {
    render(<MarkdownRenderer content="[click here](https://example.com)" />);
    const link = screen.getByText("click here");
    expect(link).toHaveAttribute("target", "_blank");
    expect(link).toHaveAttribute("rel", "noopener noreferrer");
  });
});
