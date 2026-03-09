"use client";

import { useState, useCallback, type KeyboardEvent } from "react";

interface MessageInputProps {
  onSubmit: (message: string) => void;
  disabled: boolean;
  maxLength?: number;
}

export function MessageInput({
  onSubmit,
  disabled,
  maxLength = 2000,
}: MessageInputProps) {
  const [value, setValue] = useState("");

  const trimmed = value.trim();
  const charCount = value.length;
  const isOverLimit = charCount > maxLength;
  const canSubmit = trimmed.length > 0 && !isOverLimit && !disabled;

  const handleSubmit = useCallback(() => {
    if (!canSubmit) return;
    onSubmit(trimmed);
    setValue("");
  }, [canSubmit, trimmed, onSubmit]);

  const handleKeyDown = useCallback(
    (e: KeyboardEvent<HTMLTextAreaElement>) => {
      if (e.key === "Enter" && !e.shiftKey) {
        e.preventDefault();
        handleSubmit();
      }
    },
    [handleSubmit],
  );

  return (
    <div className="flex flex-col gap-2">
      <textarea
        value={value}
        onChange={(e) => setValue(e.target.value)}
        onKeyDown={handleKeyDown}
        disabled={disabled}
        placeholder="Type your message..."
        aria-label="Support message"
        rows={3}
        className="min-h-[44px] w-full resize-none rounded-lg border border-gray-300 px-4 py-3 text-base sm:text-sm placeholder:text-gray-400 focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-500 focus-visible:ring-2 focus-visible:ring-blue-500 focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:bg-gray-100"
      />
      <div className="flex items-center justify-between">
        <span
          className={`text-xs ${
            isOverLimit ? "font-medium text-red-600" : "text-gray-400"
          }`}
        >
          {charCount} / {maxLength}
        </span>
        <button
          onClick={handleSubmit}
          disabled={!canSubmit}
          className="min-h-[44px] rounded-lg bg-blue-600 px-5 py-2 text-base sm:text-sm font-medium text-white hover:bg-blue-700 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:bg-gray-300"
        >
          Send
        </button>
      </div>
    </div>
  );
}
