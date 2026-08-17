import { createBrowserRouter, RouterProvider } from "react-router-dom";
import { AppShell } from "@/components/layout/AppShell";
import { ProtectedRoute } from "@/components/layout/ProtectedRoute";
import { LoginPage } from "@/features/auth/LoginPage";
import { RegisterPage } from "@/features/auth/RegisterPage";
import { DashboardPage } from "@/features/dashboard/DashboardPage";
import { CustomersPage } from "@/features/customers/CustomersPage";
import { ProductsPage } from "@/features/products/ProductsPage";
import { OrdersPage } from "@/features/orders/OrdersPage";
import { TasksPage } from "@/features/tasks/TasksPage";
import { CopilotPage } from "@/features/copilot/CopilotPage";
import { ReportsPage } from "@/features/reports/ReportsPage";
import { ImportsPage } from "@/features/imports/ImportsPage";

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
          { path: "/orders", element: <OrdersPage /> },
          { path: "/tasks", element: <TasksPage /> },
          { path: "/copilot", element: <CopilotPage /> },
          { path: "/reports", element: <ReportsPage /> },
          { path: "/imports", element: <ImportsPage /> },
        ],
      },
    ],
  },
]);

export function AppRouter() {
  return <RouterProvider router={router} />;
}
