import { useQuery } from "@tanstack/react-query";
import { NavLink, Outlet } from "react-router-dom";
import { Button } from "@/components/ui/Button";
import { getCurrentOrganization } from "@/features/auth/api";
import { useAuth } from "@/features/auth/AuthContext";

const NAV_ITEMS = [
  { to: "/", label: "Dashboard", end: true },
  { to: "/customers", label: "Customers" },
  { to: "/products", label: "Products" },
  { to: "/orders", label: "Orders" },
  { to: "/tasks", label: "Tasks" },
  { to: "/copilot", label: "AI Copilot" },
  { to: "/reports", label: "Reports" },
  { to: "/imports", label: "Imports" },
];

export function AppShell() {
  const { me, logout } = useAuth();
  const { data: organization } = useQuery({
    queryKey: ["organization", "current"],
    queryFn: getCurrentOrganization,
  });

  return (
    <div className="flex min-h-screen bg-slate-950 text-slate-100">
      <aside className="flex w-56 flex-col border-r border-slate-800 bg-slate-950 px-4 py-6">
        <div className="mb-8 px-2">
          <p className="text-sm font-semibold">AI Operations Copilot</p>
        </div>
        <nav className="flex flex-1 flex-col gap-1">
          {NAV_ITEMS.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              end={item.end}
              className={({ isActive }) =>
                `rounded-md px-3 py-2 text-sm font-medium transition-colors ${
                  isActive
                    ? "bg-indigo-500/15 text-indigo-300"
                    : "text-slate-400 hover:bg-slate-900 hover:text-slate-200"
                }`
              }
            >
              {item.label}
            </NavLink>
          ))}
        </nav>
      </aside>

      <div className="flex min-w-0 flex-1 flex-col">
        <header className="flex items-center justify-between border-b border-slate-800 px-6 py-4">
          <div>
            <p className="text-sm font-medium text-slate-200">
              {organization?.name ?? " "}
            </p>
            <p className="text-xs text-slate-500">
              {me?.user.full_name} &middot; <span className="uppercase">{me?.role}</span>
            </p>
          </div>
          <Button variant="secondary" onClick={() => void logout()}>
            Log out
          </Button>
        </header>

        <main className="flex-1 overflow-x-hidden overflow-y-auto p-6">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
