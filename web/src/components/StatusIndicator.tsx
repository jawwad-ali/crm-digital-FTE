"use client";

interface StatusIndicatorProps {
  isHealthy: boolean | null;
  isProcessing: boolean;
  error: string | null;
  onRetry?: () => void;
}

export function StatusIndicator({
  isHealthy,
  isProcessing,
  error,
  onRetry,
}: StatusIndicatorProps) {
  return (
    <div className="flex flex-col gap-2">
      {/* Health status dot */}
      <div className="flex items-center gap-2 text-sm" aria-live="polite">
        <span
          className={`inline-block h-2.5 w-2.5 rounded-full ${
            isHealthy === null
              ? "bg-gray-400"
              : isHealthy
                ? "bg-green-500"
                : "bg-red-500"
          }`}
          aria-hidden="true"
        />
        <span className="text-gray-600">
          {isHealthy === null
            ? "Checking connection..."
            : isHealthy
              ? "Connected"
              : "Service unavailable"}
        </span>
      </div>

      {/* Processing spinner */}
      {isProcessing && (
        <div
          className="flex items-center gap-2 text-sm text-blue-600"
          role="status"
          aria-live="polite"
          aria-busy="true"
        >
          <span className="flex gap-1" aria-hidden="true">
            <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-blue-600 [animation-delay:-0.3s]" />
            <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-blue-600 [animation-delay:-0.15s]" />
            <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-blue-600" />
          </span>
          <span>Processing your request...</span>
        </div>
      )}

      {/* Error banner */}
      {error && (
        <div
          className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-2 sm:gap-0 rounded-md border border-red-200 bg-red-50 px-3 py-2.5 sm:px-4 sm:py-3 text-sm text-red-700"
          role="alert"
        >
          <span>{error}</span>
          {onRetry && (
            <button
              onClick={onRetry}
              className="min-h-[44px] flex items-center sm:ml-4 font-medium text-red-700 underline hover:text-red-900 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-red-500 focus-visible:ring-offset-2"
            >
              Try Again
            </button>
          )}
        </div>
      )}
    </div>
  );
}
