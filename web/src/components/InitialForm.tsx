"use client";

import { useState, useCallback, type FormEvent } from "react";
import type { ValidationErrors } from "@/lib/types";

interface InitialFormProps {
  onSubmit: (name: string, email: string, message: string) => void;
  isSubmitting: boolean;
  isCoolingDown?: boolean;
}

const EMAIL_REGEX = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
const MAX_MESSAGE_LENGTH = 2000;

export function InitialForm({ onSubmit, isSubmitting, isCoolingDown = false }: InitialFormProps) {
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [message, setMessage] = useState("");
  const [errors, setErrors] = useState<ValidationErrors>({});

  const validate = useCallback((): ValidationErrors => {
    const errs: ValidationErrors = {};
    if (!name.trim()) errs.name = "Name is required";
    if (!email.trim()) {
      errs.email = "Email is required";
    } else if (!EMAIL_REGEX.test(email.trim())) {
      errs.email = "Invalid email format";
    }
    if (!message.trim()) {
      errs.message = "Message is required";
    } else if (message.length > MAX_MESSAGE_LENGTH) {
      errs.message = `Message exceeds ${MAX_MESSAGE_LENGTH} characters`;
    }
    return errs;
  }, [name, email, message]);

  const handleSubmit = useCallback(
    (e: FormEvent) => {
      e.preventDefault();
      const errs = validate();
      setErrors(errs);
      if (Object.keys(errs).length > 0) return;
      onSubmit(name.trim(), email.trim(), message.trim());
    },
    [validate, onSubmit, name, email, message],
  );

  const charCount = message.length;
  const isOverLimit = charCount > MAX_MESSAGE_LENGTH;
  const isApproachingLimit = charCount >= MAX_MESSAGE_LENGTH * 0.9 && !isOverLimit;

  return (
    <form onSubmit={handleSubmit} noValidate className="flex flex-col gap-4">
      {/* Name field */}
      <div className="flex flex-col gap-1">
        <label htmlFor="support-name" className="text-sm font-medium text-gray-700">
          Name
        </label>
        <input
          id="support-name"
          type="text"
          value={name}
          onChange={(e) => setName(e.target.value)}
          disabled={isSubmitting}
          aria-describedby={errors.name ? "name-error" : undefined}
          aria-invalid={!!errors.name}
          className="rounded-lg border border-gray-300 px-4 py-2.5 text-sm placeholder:text-gray-400 focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:cursor-not-allowed disabled:bg-gray-100"
          placeholder="Your name"
        />
        {errors.name && (
          <p id="name-error" className="text-xs text-red-600" role="alert">
            {errors.name}
          </p>
        )}
      </div>

      {/* Email field */}
      <div className="flex flex-col gap-1">
        <label htmlFor="support-email" className="text-sm font-medium text-gray-700">
          Email
        </label>
        <input
          id="support-email"
          type="email"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          disabled={isSubmitting}
          aria-describedby={errors.email ? "email-error" : undefined}
          aria-invalid={!!errors.email}
          className="rounded-lg border border-gray-300 px-4 py-2.5 text-sm placeholder:text-gray-400 focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:cursor-not-allowed disabled:bg-gray-100"
          placeholder="you@example.com"
        />
        {errors.email && (
          <p id="email-error" className="text-xs text-red-600" role="alert">
            {errors.email}
          </p>
        )}
      </div>

      {/* Message field */}
      <div className="flex flex-col gap-1">
        <label htmlFor="support-message" className="text-sm font-medium text-gray-700">
          Message
        </label>
        <textarea
          id="support-message"
          value={message}
          onChange={(e) => setMessage(e.target.value)}
          disabled={isSubmitting}
          rows={4}
          aria-describedby={errors.message ? "message-error" : undefined}
          aria-invalid={!!errors.message}
          className="w-full resize-none rounded-lg border border-gray-300 px-4 py-2.5 text-sm placeholder:text-gray-400 focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:cursor-not-allowed disabled:bg-gray-100"
          placeholder="How can we help you?"
        />
        <div className="flex items-center justify-between">
          {errors.message ? (
            <p id="message-error" className="text-xs text-red-600" role="alert">
              {errors.message}
            </p>
          ) : (
            <span />
          )}
          <span
            className={`text-xs ${
              isOverLimit
                ? "font-medium text-red-600"
                : isApproachingLimit
                  ? "font-medium text-amber-600"
                  : "text-gray-400"
            }`}
          >
            {charCount} / {MAX_MESSAGE_LENGTH}
          </span>
        </div>
      </div>

      {/* Submit button */}
      <button
        type="submit"
        disabled={isSubmitting || isCoolingDown}
        className="rounded-lg bg-blue-600 px-5 py-2.5 text-sm font-medium text-white hover:bg-blue-700 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:bg-gray-300"
      >
        {isCoolingDown ? "Please wait..." : isSubmitting ? "Sending..." : "Send Message"}
      </button>
    </form>
  );
}
