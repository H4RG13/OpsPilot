import { CustomerActivityCard } from "@/features/dashboard/CustomerActivityCard";
import { KpiCards } from "@/features/dashboard/KpiCards";
import { RecentOrdersCard } from "@/features/dashboard/RecentOrdersCard";
import { RecentTasksCard } from "@/features/dashboard/RecentTasksCard";
import { RevenueChart } from "@/features/dashboard/RevenueChart";
import { TopProductsCard } from "@/features/dashboard/TopProductsCard";

export function DashboardPage() {
  return (
    <div className="flex flex-col gap-6">
      <div>
        <h1 className="text-2xl font-semibold text-slate-100">Dashboard</h1>
        <p className="mt-1 text-sm text-slate-400">Trailing 30 days, unless noted otherwise.</p>
      </div>

      <KpiCards />

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
        <div className="lg:col-span-2">
          <RevenueChart />
        </div>
        <TopProductsCard />
      </div>

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
        <CustomerActivityCard />
        <RecentOrdersCard />
        <RecentTasksCard />
      </div>
    </div>
  );
}
