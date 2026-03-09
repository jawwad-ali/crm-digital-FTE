"use client";

import { useState, useCallback } from "react";
import type { Conversation, Message } from "@/lib/types";

const initialConversation: Conversation = {
  messages: [],
  customerName: "",
  customerEmail: "",
  isFollowUpMode: false,
};

export function useConversation() {
  const [conversation, setConversation] =
    useState<Conversation>(initialConversation);

  const addCustomerMessage = useCallback((content: string): Message => {
    const message: Message = {
      id: crypto.randomUUID(),
      role: "customer",
      content,
      timestamp: new Date(),
      status: "sent",
    };

    setConversation((prev) => ({
      ...prev,
      messages: [...prev.messages, message],
    }));

    return message;
  }, []);

  const updateMessageStatus = useCallback(
    (
      id: string,
      status: Message["status"],
      response?: string,
      error?: string,
    ) => {
      setConversation((prev) => {
        const messages = prev.messages.map((msg) =>
          msg.id === id ? { ...msg, status, error } : msg,
        );

        // When a customer message completes, append the agent response
        if (status === "completed" && response) {
          const agentMessage: Message = {
            id: crypto.randomUUID(),
            role: "agent",
            content: response,
            timestamp: new Date(),
            status: "completed",
          };
          messages.push(agentMessage);
        }

        return {
          ...prev,
          messages,
          isFollowUpMode: prev.isFollowUpMode || status === "completed",
        };
      });
    },
    [],
  );

  const setCustomerInfo = useCallback((name: string, email: string) => {
    setConversation((prev) => ({
      ...prev,
      customerName: name,
      customerEmail: email,
    }));
  }, []);

  return { conversation, addCustomerMessage, updateMessageStatus, setCustomerInfo };
}
