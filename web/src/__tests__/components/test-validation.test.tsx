import { render, screen, fireEvent } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { InitialForm } from "@/components/InitialForm";

function fillField(label: string, value: string) {
  fireEvent.change(screen.getByLabelText(label), { target: { value } });
}

describe("InitialForm validation", () => {
  const onSubmit = vi.fn();

  beforeEach(() => {
    onSubmit.mockReset();
  });

  it("shows errors for all empty fields on submit", async () => {
    const user = userEvent.setup();
    render(<InitialForm onSubmit={onSubmit} isSubmitting={false} />);

    await user.click(screen.getByRole("button", { name: "Send Message" }));

    expect(screen.getByText("Name is required")).toBeInTheDocument();
    expect(screen.getByText("Email is required")).toBeInTheDocument();
    expect(screen.getByText("Message is required")).toBeInTheDocument();
    expect(onSubmit).not.toHaveBeenCalled();
  });

  it("shows error for invalid email format", async () => {
    const user = userEvent.setup();
    render(<InitialForm onSubmit={onSubmit} isSubmitting={false} />);

    fillField("Name", "Ali");
    fillField("Email", "not-an-email");
    fillField("Message", "Help");
    await user.click(screen.getByRole("button", { name: "Send Message" }));

    expect(screen.getByText("Invalid email format")).toBeInTheDocument();
    expect(onSubmit).not.toHaveBeenCalled();
  });

  it("shows error for message exceeding 2000 characters", async () => {
    const user = userEvent.setup();
    render(<InitialForm onSubmit={onSubmit} isSubmitting={false} />);

    fillField("Name", "Ali");
    fillField("Email", "ali@test.com");
    fillField("Message", "a".repeat(2001));
    await user.click(screen.getByRole("button", { name: "Send Message" }));

    expect(screen.getByText("Message exceeds 2000 characters")).toBeInTheDocument();
    expect(onSubmit).not.toHaveBeenCalled();
  });

  it("submits valid data successfully", async () => {
    const user = userEvent.setup();
    render(<InitialForm onSubmit={onSubmit} isSubmitting={false} />);

    fillField("Name", "Ali");
    fillField("Email", "ali@test.com");
    fillField("Message", "Help me please");
    await user.click(screen.getByRole("button", { name: "Send Message" }));

    expect(onSubmit).toHaveBeenCalledWith("Ali", "ali@test.com", "Help me please");
  });

  it("shows amber char counter when approaching 2000 limit", () => {
    render(<InitialForm onSubmit={onSubmit} isSubmitting={false} />);

    fillField("Message", "a".repeat(1800));

    const counter = screen.getByText("1800 / 2000");
    expect(counter).toHaveClass("text-amber-600");
  });

  it("shows red char counter when over 2000 limit", () => {
    render(<InitialForm onSubmit={onSubmit} isSubmitting={false} />);

    fillField("Message", "a".repeat(2001));

    const counter = screen.getByText("2001 / 2000");
    expect(counter).toHaveClass("text-red-600");
  });

  it("shows normal char counter under 90% of limit", () => {
    render(<InitialForm onSubmit={onSubmit} isSubmitting={false} />);

    fillField("Message", "Hello");

    const counter = screen.getByText("5 / 2000");
    expect(counter).toHaveClass("text-gray-400");
    expect(counter).not.toHaveClass("text-amber-600");
    expect(counter).not.toHaveClass("text-red-600");
  });

  it("shows 'Please wait...' on button when cooling down", () => {
    render(<InitialForm onSubmit={onSubmit} isSubmitting={false} isCoolingDown={true} />);

    const button = screen.getByRole("button", { name: "Please wait..." });
    expect(button).toBeDisabled();
  });

  it("sets aria-invalid and aria-describedby on invalid fields", async () => {
    const user = userEvent.setup();
    render(<InitialForm onSubmit={onSubmit} isSubmitting={false} />);

    await user.click(screen.getByRole("button", { name: "Send Message" }));

    const nameInput = screen.getByLabelText("Name");
    expect(nameInput).toHaveAttribute("aria-invalid", "true");
    expect(nameInput).toHaveAttribute("aria-describedby", "name-error");

    const emailInput = screen.getByLabelText("Email");
    expect(emailInput).toHaveAttribute("aria-invalid", "true");
    expect(emailInput).toHaveAttribute("aria-describedby", "email-error");
  });
});
