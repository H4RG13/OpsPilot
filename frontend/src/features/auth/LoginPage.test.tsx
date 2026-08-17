import { describe, expect, it, vi } from "vitest";
import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { renderWithProviders } from "@/test/test-utils";
import { LoginPage } from "@/features/auth/LoginPage";
import { useAuth } from "@/features/auth/AuthContext";

vi.mock("@/features/auth/AuthContext", () => ({
  useAuth: vi.fn(),
}));

const mockedUseAuth = vi.mocked(useAuth);

describe("LoginPage", () => {
  it("submits the entered credentials", async () => {
    const login = vi.fn().mockResolvedValue(undefined);
    mockedUseAuth.mockReturnValue({
      login,
      register: vi.fn(),
      logout: vi.fn(),
      me: null,
      isLoading: false,
      isAuthenticated: false,
    });

    renderWithProviders(<LoginPage />, { route: "/login" });

    await userEvent.type(screen.getByLabelText("Email"), "demo@acme.example");
    await userEvent.type(screen.getByLabelText("Password"), "supersecret123");
    await userEvent.click(screen.getByRole("button", { name: "Sign in" }));

    await waitFor(() => {
      expect(login).toHaveBeenCalledWith({
        email: "demo@acme.example",
        password: "supersecret123",
      });
    });
  });

  it("shows an error message when login fails, without navigating away", async () => {
    const login = vi.fn().mockRejectedValue(new Error("Invalid credentials"));
    mockedUseAuth.mockReturnValue({
      login,
      register: vi.fn(),
      logout: vi.fn(),
      me: null,
      isLoading: false,
      isAuthenticated: false,
    });

    renderWithProviders(<LoginPage />, { route: "/login" });

    await userEvent.type(screen.getByLabelText("Email"), "demo@acme.example");
    await userEvent.type(screen.getByLabelText("Password"), "wrong-password");
    await userEvent.click(screen.getByRole("button", { name: "Sign in" }));

    expect(await screen.findByText("Invalid credentials")).toBeInTheDocument();
  });
});
