import { describe, expect, it, vi } from "vitest";
import { screen } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { render } from "@testing-library/react";
import { ProtectedRoute } from "@/components/layout/ProtectedRoute";
import { useAuth } from "@/features/auth/AuthContext";

vi.mock("@/features/auth/AuthContext", () => ({
  useAuth: vi.fn(),
}));

const mockedUseAuth = vi.mocked(useAuth);

function renderProtectedRoute(initialEntry: string) {
  return render(
    <MemoryRouter initialEntries={[initialEntry]}>
      <Routes>
        <Route path="/login" element={<div>Login Page</div>} />
        <Route element={<ProtectedRoute />}>
          <Route path="/" element={<div>Dashboard Page</div>} />
        </Route>
      </Routes>
    </MemoryRouter>
  );
}

describe("ProtectedRoute", () => {
  it("shows a spinner while the session is loading", () => {
    mockedUseAuth.mockReturnValue({
      login: vi.fn(),
      register: vi.fn(),
      logout: vi.fn(),
      me: null,
      isLoading: true,
      isAuthenticated: false,
    });

    const { container } = renderProtectedRoute("/");

    expect(screen.queryByText("Dashboard Page")).not.toBeInTheDocument();
    expect(screen.queryByText("Login Page")).not.toBeInTheDocument();
    expect(container.querySelector(".animate-spin")).toBeInTheDocument();
  });

  it("redirects to /login when unauthenticated", () => {
    mockedUseAuth.mockReturnValue({
      login: vi.fn(),
      register: vi.fn(),
      logout: vi.fn(),
      me: null,
      isLoading: false,
      isAuthenticated: false,
    });

    renderProtectedRoute("/");

    expect(screen.getByText("Login Page")).toBeInTheDocument();
  });

  it("renders the protected content when authenticated", () => {
    mockedUseAuth.mockReturnValue({
      login: vi.fn(),
      register: vi.fn(),
      logout: vi.fn(),
      me: {
        user: { id: "1", email: "a@b.com", full_name: "A", created_at: "" },
        organization_id: "org-1",
        role: "owner",
      },
      isLoading: false,
      isAuthenticated: true,
    });

    renderProtectedRoute("/");

    expect(screen.getByText("Dashboard Page")).toBeInTheDocument();
  });
});
