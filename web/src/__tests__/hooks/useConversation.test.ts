import { renderHook, act } from "@testing-library/react";
import { useConversation } from "@/hooks/useConversation";

describe("useConversation", () => {
  it("initializes with empty conversation state", () => {
    const { result } = renderHook(() => useConversation());

    expect(result.current.conversation).toEqual({
      messages: [],
      customerName: "",
      customerEmail: "",
      isFollowUpMode: false,
    });
  });

  it("adds a customer message with correct defaults", () => {
    const { result } = renderHook(() => useConversation());

    let message: ReturnType<typeof result.current.addCustomerMessage>;
    act(() => {
      message = result.current.addCustomerMessage("Hello, I need help");
    });

    expect(message!.role).toBe("customer");
    expect(message!.content).toBe("Hello, I need help");
    expect(message!.status).toBe("sent");
    expect(message!.id).toBeDefined();
    expect(message!.timestamp).toBeInstanceOf(Date);

    expect(result.current.conversation.messages).toHaveLength(1);
    expect(result.current.conversation.messages[0].content).toBe(
      "Hello, I need help",
    );
  });

  it("adds multiple messages in order", () => {
    const { result } = renderHook(() => useConversation());

    act(() => {
      result.current.addCustomerMessage("First");
    });
    act(() => {
      result.current.addCustomerMessage("Second");
    });

    expect(result.current.conversation.messages).toHaveLength(2);
    expect(result.current.conversation.messages[0].content).toBe("First");
    expect(result.current.conversation.messages[1].content).toBe("Second");
  });

  it("updates message status to processing", () => {
    const { result } = renderHook(() => useConversation());

    let msg: ReturnType<typeof result.current.addCustomerMessage>;
    act(() => {
      msg = result.current.addCustomerMessage("Help me");
    });

    act(() => {
      result.current.updateMessageStatus(msg!.id, "processing");
    });

    expect(result.current.conversation.messages[0].status).toBe("processing");
  });

  it("appends agent message on completed status with response", () => {
    const { result } = renderHook(() => useConversation());

    let msg: ReturnType<typeof result.current.addCustomerMessage>;
    act(() => {
      msg = result.current.addCustomerMessage("Help me");
    });

    act(() => {
      result.current.updateMessageStatus(
        msg!.id,
        "completed",
        "Here is the answer",
      );
    });

    const messages = result.current.conversation.messages;
    expect(messages).toHaveLength(2);
    expect(messages[0].status).toBe("completed");
    expect(messages[1].role).toBe("agent");
    expect(messages[1].content).toBe("Here is the answer");
    expect(messages[1].status).toBe("completed");
  });

  it("sets isFollowUpMode to true after first completed response", () => {
    const { result } = renderHook(() => useConversation());

    expect(result.current.conversation.isFollowUpMode).toBe(false);

    let msg: ReturnType<typeof result.current.addCustomerMessage>;
    act(() => {
      msg = result.current.addCustomerMessage("Help");
    });
    act(() => {
      result.current.updateMessageStatus(msg!.id, "completed", "Answer");
    });

    expect(result.current.conversation.isFollowUpMode).toBe(true);
  });

  it("keeps isFollowUpMode true for subsequent messages", () => {
    const { result } = renderHook(() => useConversation());

    let msg1: ReturnType<typeof result.current.addCustomerMessage>;
    act(() => {
      msg1 = result.current.addCustomerMessage("First");
    });
    act(() => {
      result.current.updateMessageStatus(msg1!.id, "completed", "Reply 1");
    });

    let msg2: ReturnType<typeof result.current.addCustomerMessage>;
    act(() => {
      msg2 = result.current.addCustomerMessage("Second");
    });
    act(() => {
      result.current.updateMessageStatus(msg2!.id, "processing");
    });

    // Still true even though second message is processing
    expect(result.current.conversation.isFollowUpMode).toBe(true);
  });

  it("sets error on failed status", () => {
    const { result } = renderHook(() => useConversation());

    let msg: ReturnType<typeof result.current.addCustomerMessage>;
    act(() => {
      msg = result.current.addCustomerMessage("Help");
    });
    act(() => {
      result.current.updateMessageStatus(
        msg!.id,
        "failed",
        undefined,
        "Something went wrong",
      );
    });

    expect(result.current.conversation.messages[0].status).toBe("failed");
    expect(result.current.conversation.messages[0].error).toBe(
      "Something went wrong",
    );
  });

  it("sets customer info", () => {
    const { result } = renderHook(() => useConversation());

    act(() => {
      result.current.setCustomerInfo("Ali", "ali@test.com");
    });

    expect(result.current.conversation.customerName).toBe("Ali");
    expect(result.current.conversation.customerEmail).toBe("ali@test.com");
  });
});
