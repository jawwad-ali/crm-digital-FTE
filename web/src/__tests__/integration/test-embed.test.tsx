import { render, screen, waitFor } from "@testing-library/react";
import * as api from "@/lib/api";
import EmbedPage from "@/app/embed/page";

vi.mock("@/lib/api", () => ({
  submitChat: vi.fn(),
  getJobStatus: vi.fn(),
  checkHealth: vi.fn(),
}));

const mockedCheckHealth = vi.mocked(api.checkHealth);

describe("Embed page", () => {
  beforeEach(() => {
    mockedCheckHealth.mockResolvedValue(true);
  });

  it("renders SupportForm", async () => {
    render(<EmbedPage />);

    await waitFor(() => {
      expect(screen.getByText("Connected")).toBeInTheDocument();
    });

    // SupportForm present — has the initial form fields
    expect(screen.getByLabelText("Name")).toBeInTheDocument();
    expect(screen.getByLabelText("Email")).toBeInTheDocument();
    expect(screen.getByLabelText("Message")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Send Message" })).toBeInTheDocument();
  });

  it("does not render page header or nav elements", () => {
    render(<EmbedPage />);

    // No heading, nav, header, or footer from the main page
    expect(screen.queryByRole("heading")).not.toBeInTheDocument();
    expect(screen.queryByRole("navigation")).not.toBeInTheDocument();
    expect(screen.queryByRole("banner")).not.toBeInTheDocument();
    expect(screen.queryByRole("contentinfo")).not.toBeInTheDocument();
  });
});
