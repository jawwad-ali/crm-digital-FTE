import { renderHook, act } from "@testing-library/react";
import { useCooldown } from "@/hooks/useCooldown";

describe("useCooldown", () => {
  beforeEach(() => {
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it("starts with isCoolingDown false", () => {
    const { result } = renderHook(() => useCooldown(5000));
    expect(result.current.isCoolingDown).toBe(false);
  });

  it("sets isCoolingDown true after startCooldown", () => {
    const { result } = renderHook(() => useCooldown(5000));

    act(() => {
      result.current.startCooldown();
    });

    expect(result.current.isCoolingDown).toBe(true);
  });

  it("resets isCoolingDown after duration expires", () => {
    const { result } = renderHook(() => useCooldown(5000));

    act(() => {
      result.current.startCooldown();
    });

    expect(result.current.isCoolingDown).toBe(true);

    act(() => {
      vi.advanceTimersByTime(5000);
    });

    expect(result.current.isCoolingDown).toBe(false);
  });

  it("stays cooling down before duration expires", () => {
    const { result } = renderHook(() => useCooldown(10000));

    act(() => {
      result.current.startCooldown();
    });

    act(() => {
      vi.advanceTimersByTime(5000);
    });

    expect(result.current.isCoolingDown).toBe(true);

    act(() => {
      vi.advanceTimersByTime(5000);
    });

    expect(result.current.isCoolingDown).toBe(false);
  });

  it("uses default 10s duration", () => {
    const { result } = renderHook(() => useCooldown());

    act(() => {
      result.current.startCooldown();
    });

    act(() => {
      vi.advanceTimersByTime(9999);
    });
    expect(result.current.isCoolingDown).toBe(true);

    act(() => {
      vi.advanceTimersByTime(1);
    });
    expect(result.current.isCoolingDown).toBe(false);
  });

  it("resets timer on repeated startCooldown calls", () => {
    const { result } = renderHook(() => useCooldown(5000));

    act(() => {
      result.current.startCooldown();
    });

    // Advance 3s, then restart cooldown
    act(() => {
      vi.advanceTimersByTime(3000);
    });
    expect(result.current.isCoolingDown).toBe(true);

    act(() => {
      result.current.startCooldown();
    });

    // Original timer would have expired at 5s, but we restarted at 3s
    act(() => {
      vi.advanceTimersByTime(3000);
    });
    expect(result.current.isCoolingDown).toBe(true);

    // New timer expires at 3s + 5s = 8s total
    act(() => {
      vi.advanceTimersByTime(2000);
    });
    expect(result.current.isCoolingDown).toBe(false);
  });
});
