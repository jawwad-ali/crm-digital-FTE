import { renderHook, waitFor } from "@testing-library/react";
import { useHealthCheck } from "@/hooks/useHealthCheck";
import * as api from "@/lib/api";

vi.mock("@/lib/api", () => ({
  checkHealth: vi.fn(),
}));

const mockedCheckHealth = vi.mocked(api.checkHealth);

describe("useHealthCheck", () => {
  beforeEach(() => {
    mockedCheckHealth.mockReset();
  });

  it("starts with null (loading state)", () => {
    mockedCheckHealth.mockReturnValue(new Promise(() => {})); // never resolves

    const { result } = renderHook(() => useHealthCheck());
    expect(result.current.isHealthy).toBeNull();
  });

  it("returns true when backend is healthy", async () => {
    mockedCheckHealth.mockResolvedValue(true);

    const { result } = renderHook(() => useHealthCheck());

    await waitFor(() => {
      expect(result.current.isHealthy).toBe(true);
    });
  });

  it("returns false when backend is unhealthy", async () => {
    mockedCheckHealth.mockResolvedValue(false);

    const { result } = renderHook(() => useHealthCheck());

    await waitFor(() => {
      expect(result.current.isHealthy).toBe(false);
    });
  });

  it("calls checkHealth only once on mount", async () => {
    mockedCheckHealth.mockResolvedValue(true);

    const { result } = renderHook(() => useHealthCheck());

    await waitFor(() => {
      expect(result.current.isHealthy).toBe(true);
    });

    expect(mockedCheckHealth).toHaveBeenCalledTimes(1);
  });
});
