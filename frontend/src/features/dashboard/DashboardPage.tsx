import { Card } from "@/components/ui/Card";

export function DashboardPage() {
  return (
    <div className="flex flex-col gap-4">
      <div>
        <h1 className="text-2xl font-semibold text-slate-100">Dashboard</h1>
        <p className="mt-1 text-sm text-slate-400">
          KPI cards, revenue trend, and recent activity are coming in Phase 12.
        </p>
      </div>
      <Card>
        <p className="text-sm text-slate-400">
          You're signed in and the app shell is wired up — this is where the
          real dashboard widgets will live.
        </p>
      </Card>
    </div>
  );
}
