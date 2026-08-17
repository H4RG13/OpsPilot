import { describe, expect, it, vi } from "vitest";
import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { renderWithProviders } from "@/test/test-utils";
import { RegisterPage } from "@/features/auth/RegisterPage";
import { useAuth } from "@/features/auth/AuthContext";

vi.mock("@/features/auth/AuthContext", () => ({
  useAuth: vi.fn(),
}));

const mockedUseAuth = vi.mocked(useAuth);

async function fillCommonFields() {
  await userEvent.type(screen.getByLabelText("Your name"), "Jane Owner");
  await userEvent.type(screen.getByLabelText("Organization name"), "Acme Inc");
  await userEvent.type(screen.getByLabelText("Email"), "jane@acme.example");
}

describe("RegisterPage", () => {
  it("rejects a password shorter than 8 characters without calling register", async () => {
    const register = vi.fn();
    mockedUseAuth.mockReturnValue({
      login: vi.fn(),
      register,
      logout: vi.fn(),
      me: null,
      isLoading: false,
      isAuthenticated: false,
    });

    renderWithProviders(<RegisterPage />, { route: "/register" });

    await fillCommonFields();
    await userEvent.type(screen.getByLabelText("Password"), "short");
    await userEvent.click(screen.getByRole("button", { name: "Create account" }));

    expect(
      await screen.findByText("Password must be at least 8 characters.")
    ).toBeInTheDocument();
    expect(register).not.toHaveBeenCalled();
  });

  it("submits registration details when the password is valid", async () => {
    const register = vi.fn().mockResolvedValue(undefined);
    mockedUseAuth.mockReturnValue({
      login: vi.fn(),
      register,
      logout: vi.fn(),
      me: null,
      isLoading: false,
      isAuthenticated: false,
    });

    renderWithProviders(<RegisterPage />, { route: "/register" });

    await fillCommonFields();
    await userEvent.type(screen.getByLabelText("Password"), "supersecret123");
    await userEvent.click(screen.getByRole("button", { name: "Create account" }));

    expect(register).toHaveBeenCalledWith({
      email: "jane@acme.example",
      password: "supersecret123",
      full_name: "Jane Owner",
      organization_name: "Acme Inc",
    });
  });
});
