import { createBrowserRouter, RouterProvider } from "react-router-dom";
import { AppShell } from "@/components/layout/AppShell";
import { ProtectedRoute } from "@/components/layout/ProtectedRoute";
import { ComingSoon } from "@/components/common/ComingSoon";
import { LoginPage } from "@/features/auth/LoginPage";
import { RegisterPage } from "@/features/auth/RegisterPage";
import { DashboardPage } from "@/features/dashboard/DashboardPage";
import { CustomersPage } from "@/features/customers/CustomersPage";
import { ProductsPage } from "@/features/products/ProductsPage";

const router = createBrowserRouter([
  { path: "/login", element: <LoginPage /> },
  { path: "/register", element: <RegisterPage /> },
  {
    element: <ProtectedRoute />,
    children: [
      {
        element: <AppShell />,
        children: [
          { path: "/", element: <DashboardPage /> },
          { path: "/customers", element: <CustomersPage /> },
          { path: "/products", element: <ProductsPage /> },
          { path: "/orders", element: <ComingSoon title="Orders" /> },
          { path: "/tasks", element: <ComingSoon title="Tasks" /> },
          { path: "/copilot", element: <ComingSoon title="AI Copilot" /> },
          { path: "/reports", element: <ComingSoon title="Reports" /> },
          { path: "/imports", element: <ComingSoon title="Imports" /> },
        ],
      },
    ],
  },
]);

export function AppRouter() {
  return <RouterProvider router={router} />;
}
