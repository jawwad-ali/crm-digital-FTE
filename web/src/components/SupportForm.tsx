"use client";

import { useCallback, useState } from "react";
import { useConversation } from "@/hooks/useConversation";
import { useHealthCheck } from "@/hooks/useHealthCheck";
import { useJobPolling } from "@/hooks/useJobPolling";
import { useCooldown } from "@/hooks/useCooldown";
import { submitChat } from "@/lib/api";
import { InitialForm } from "./InitialForm";
import { ChatThread } from "./ChatThread";
import { CustomerHeader } from "./CustomerHeader";
import { MessageInput } from "./MessageInput";
import { StatusIndicator } from "./StatusIndicator";

export function SupportForm() {
  const {
    conversation,
    addCustomerMessage,
    updateMessageStatus,
    setCustomerInfo,
  } = useConversation();
  const { isHealthy } = useHealthCheck();
  const { isCoolingDown, startCooldown } = useCooldown();

  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [activeJobId, setActiveJobId] = useState<string | null>(null);
  const [activeMessageId, setActiveMessageId] = useState<string | null>(null);
  const [lastSubmission, setLastSubmission] = useState<{
    name: string;
    email: string;
    message: string;
  } | null>(null);

  const handlePollComplete = useCallback(
    (response: string) => {
      if (activeMessageId) {
        updateMessageStatus(activeMessageId, "completed", response);
      }
      setActiveJobId(null);
      setActiveMessageId(null);
      setIsSubmitting(false);
      setError(null);
      setLastSubmission(null);
      startCooldown();
    },
    [activeMessageId, updateMessageStatus, startCooldown],
  );

  const handlePollError = useCallback(
    (errMsg: string) => {
      if (activeMessageId) {
        updateMessageStatus(activeMessageId, "failed", undefined, errMsg);
      }
      setActiveJobId(null);
      setActiveMessageId(null);
      setIsSubmitting(false);
      setError(errMsg);
    },
    [activeMessageId, updateMessageStatus],
  );

  const { isPolling } = useJobPolling(
    activeJobId,
    handlePollComplete,
    handlePollError,
  );

  const handleSubmit = useCallback(
    async (name: string, email: string, messageText: string) => {
      setIsSubmitting(true);
      setError(null);
      setLastSubmission({ name, email, message: messageText });

      // Store customer info on first submission
      if (!conversation.isFollowUpMode) {
        setCustomerInfo(name, email);
      }

      // Add customer message to thread
      const msg = addCustomerMessage(messageText);
      setActiveMessageId(msg.id);
      updateMessageStatus(msg.id, "processing");

      try {
        const job = await submitChat({
          name,
          email,
          message: messageText,
          channel: "web",
        });
        setActiveJobId(job.job_id);
      } catch (err) {
        const errMsg =
          err instanceof Error ? err.message : "Failed to send message";
        updateMessageStatus(msg.id, "failed", undefined, errMsg);
        setActiveMessageId(null);
        setIsSubmitting(false);
        setError(errMsg);
      }
    },
    [
      conversation.isFollowUpMode,
      setCustomerInfo,
      addCustomerMessage,
      updateMessageStatus,
    ],
  );

  const handleInitialSubmit = useCallback(
    (name: string, email: string, message: string) => {
      handleSubmit(name, email, message);
    },
    [handleSubmit],
  );

  const handleFollowUpSubmit = useCallback(
    (message: string) => {
      handleSubmit(
        conversation.customerName,
        conversation.customerEmail,
        message,
      );
    },
    [handleSubmit, conversation.customerName, conversation.customerEmail],
  );

  const handleRetry = useCallback(() => {
    setError(null);
    if (lastSubmission) {
      handleSubmit(
        lastSubmission.name,
        lastSubmission.email,
        lastSubmission.message,
      );
    }
  }, [lastSubmission, handleSubmit]);

  const isProcessing = isSubmitting || isPolling;

  return (
    <div className="flex flex-col gap-4">
      <StatusIndicator
        isHealthy={isHealthy}
        isProcessing={isProcessing}
        error={error}
        onRetry={error ? handleRetry : undefined}
      />

      {conversation.isFollowUpMode && (
        <CustomerHeader
          name={conversation.customerName}
          email={conversation.customerEmail}
        />
      )}

      <ChatThread messages={conversation.messages} />

      {conversation.isFollowUpMode ? (
        <MessageInput
          onSubmit={handleFollowUpSubmit}
          disabled={isProcessing || isCoolingDown}
        />
      ) : (
        <InitialForm
          onSubmit={handleInitialSubmit}
          isSubmitting={isProcessing}
          isCoolingDown={isCoolingDown}
        />
      )}
    </div>
  );
}
