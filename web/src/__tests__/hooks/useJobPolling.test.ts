import { renderHook, act } from "@testing-library/react";
import { useJobPolling } from "@/hooks/useJobPolling";
import * as api from "@/lib/api";

vi.mock("@/lib/api", () => ({
  getJobStatus: vi.fn(),
}));

const mockedGetJobStatus = vi.mocked(api.getJobStatus);

describe("useJobPolling", () => {
  beforeEach(() => {
    vi.useFakeTimers();
    mockedGetJobStatus.mockReset();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it("does not poll when jobId is null", () => {
    const onComplete = vi.fn();
    const onError = vi.fn();

    const { result } = renderHook(() =>
      useJobPolling(null, onComplete, onError),
    );

    expect(result.current.isPolling).toBe(false);
    expect(result.current.elapsed).toBe(0);
    expect(mockedGetJobStatus).not.toHaveBeenCalled();
  });

  it("starts polling when jobId is set and calls onComplete", async () => {
    mockedGetJobStatus.mockResolvedValueOnce({
      job_id: "job-1",
      status: "completed",
      response: "Done!",
      error: null,
      retry_after: null,
    });

    const onComplete = vi.fn();
    const onError = vi.fn();

    renderHook(() => useJobPolling("job-1", onComplete, onError));

    await act(async () => {
      await vi.advanceTimersByTimeAsync(5000);
    });

    expect(mockedGetJobStatus).toHaveBeenCalledWith("job-1");
    expect(onComplete).toHaveBeenCalledWith("Done!");
  });

  it("polls multiple times until completed", async () => {
    mockedGetJobStatus
      .mockResolvedValueOnce({
        job_id: "job-1",
        status: "processing",
        response: null,
        error: null,
        retry_after: 2,
      })
      .mockResolvedValueOnce({
        job_id: "job-1",
        status: "completed",
        response: "Here is the answer",
        error: null,
        retry_after: null,
      });

    const onComplete = vi.fn();
    const onError = vi.fn();

    renderHook(() => useJobPolling("job-1", onComplete, onError));

    // First poll at 5s — returns processing with retry_after=2
    await act(async () => {
      await vi.advanceTimersByTimeAsync(5000);
    });
    expect(mockedGetJobStatus).toHaveBeenCalledTimes(1);
    expect(onComplete).not.toHaveBeenCalled();

    // Second poll at 5s + 2s — returns completed
    await act(async () => {
      await vi.advanceTimersByTimeAsync(2000);
    });

    expect(mockedGetJobStatus).toHaveBeenCalledTimes(2);
    expect(onComplete).toHaveBeenCalledWith("Here is the answer");
  });

  it("calls onError when job fails", async () => {
    mockedGetJobStatus.mockResolvedValueOnce({
      job_id: "job-1",
      status: "failed",
      response: null,
      error: "Agent error occurred",
      retry_after: null,
    });

    const onComplete = vi.fn();
    const onError = vi.fn();

    renderHook(() => useJobPolling("job-1", onComplete, onError));

    await act(async () => {
      await vi.advanceTimersByTimeAsync(5000);
    });

    expect(onError).toHaveBeenCalledWith("Agent error occurred");
    expect(onComplete).not.toHaveBeenCalled();
  });

  it("calls onError after 3 consecutive network failures", async () => {
    mockedGetJobStatus
      .mockRejectedValueOnce(new Error("fetch failed"))
      .mockRejectedValueOnce(new Error("fetch failed"))
      .mockRejectedValueOnce(new Error("fetch failed"));

    const onComplete = vi.fn();
    const onError = vi.fn();

    renderHook(() => useJobPolling("job-1", onComplete, onError));

    // 1st attempt
    await act(async () => {
      await vi.advanceTimersByTimeAsync(5000);
    });
    // 2nd attempt
    await act(async () => {
      await vi.advanceTimersByTimeAsync(5000);
    });
    // 3rd attempt — gives up
    await act(async () => {
      await vi.advanceTimersByTimeAsync(5000);
    });

    expect(onError).toHaveBeenCalledWith(
      "Network error. Please check your connection and try again.",
    );
  });

  it("resets network failure count on successful poll", async () => {
    mockedGetJobStatus
      .mockRejectedValueOnce(new Error("Network error"))
      .mockResolvedValueOnce({
        job_id: "job-1",
        status: "processing",
        response: null,
        error: null,
        retry_after: 1,
      })
      .mockRejectedValueOnce(new Error("Network error"))
      .mockResolvedValueOnce({
        job_id: "job-1",
        status: "completed",
        response: "Done",
        error: null,
        retry_after: null,
      });

    const onComplete = vi.fn();
    const onError = vi.fn();

    renderHook(() => useJobPolling("job-1", onComplete, onError));

    // 1st: network error (failures=1)
    await act(async () => {
      await vi.advanceTimersByTimeAsync(5000);
    });
    // 2nd: success, processing (failures reset to 0)
    await act(async () => {
      await vi.advanceTimersByTimeAsync(5000);
    });
    // 3rd: network error again (failures=1, not 2)
    await act(async () => {
      await vi.advanceTimersByTimeAsync(1000);
    });
    // 4th: success, completed
    await act(async () => {
      await vi.advanceTimersByTimeAsync(5000);
    });

    expect(onComplete).toHaveBeenCalledWith("Done");
    expect(onError).not.toHaveBeenCalled();
  });

  it("times out after 5 minutes", async () => {
    mockedGetJobStatus.mockResolvedValue({
      job_id: "job-1",
      status: "processing",
      response: null,
      error: null,
      retry_after: 5,
    });

    const onComplete = vi.fn();
    const onError = vi.fn();

    renderHook(() => useJobPolling("job-1", onComplete, onError));

    // Advance past 5 minutes
    for (let i = 0; i < 62; i++) {
      await act(async () => {
        await vi.advanceTimersByTimeAsync(5000);
      });
    }

    expect(onError).toHaveBeenCalledWith(
      "Request timed out. Please try again.",
    );
  }, 15000);

  it("stops polling on unmount", async () => {
    mockedGetJobStatus.mockResolvedValue({
      job_id: "job-1",
      status: "processing",
      response: null,
      error: null,
      retry_after: 5,
    });

    const onComplete = vi.fn();
    const onError = vi.fn();

    const { unmount } = renderHook(() =>
      useJobPolling("job-1", onComplete, onError),
    );

    // First poll
    await act(async () => {
      await vi.advanceTimersByTimeAsync(5000);
    });

    unmount();

    const callCount = mockedGetJobStatus.mock.calls.length;
    await act(async () => {
      await vi.advanceTimersByTimeAsync(10000);
    });

    expect(mockedGetJobStatus.mock.calls.length).toBe(callCount);
  });
});
