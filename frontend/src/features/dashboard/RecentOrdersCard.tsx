import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { Card } from "@/components/ui/Card";
import { QueryState } from "@/components/common/QueryState";
import { getRecentOrders } from "@/features/dashboard/api";
import { formatCurrency } from "@/lib/format";
import type { OrderStatus } from "@/types/orders";

const STATUS_STYLES: Record<OrderStatus, string> = {
  pending: "bg-amber-500/15 text-amber-300",
  completed: "bg-emerald-500/15 text-emerald-300",
  cancelled: "bg-slate-700 text-slate-400",
};

export function RecentOrdersCard() {
  const { data, isLoading, isError, error } = useQuery({
    queryKey: ["orders", "recent"],
    queryFn: () => getRecentOrders(5),
  });

  return (
    <Card>
      <div className="flex items-center justify-between">
        <h2 className="text-sm font-semibold text-slate-200">Recent Orders</h2>
        <Link to="/orders" className="text-xs text-indigo-400 hover:text-indigo-300">
          View all
        </Link>
      </div>
      <div className="mt-4">
        <QueryState
          isLoading={isLoading}
          isError={isError}
          error={error}
          isEmpty={!isLoading && !isError && (data?.items.length ?? 0) === 0}
          emptyMessage="No orders yet."
        >
          <ul className="divide-y divide-slate-800">
            {data?.items.map((order) => (
              <li key={order.id} className="flex items-center justify-between py-2 text-sm">
                <span className="text-slate-400">
                  {new Date(order.ordered_at).toLocaleDateString()}
                </span>
                <span className={`rounded-full px-2 py-0.5 text-xs capitalize ${STATUS_STYLES[order.status]}`}>
                  {order.status}
                </span>
                <span className="text-slate-200">{formatCurrency(order.total_amount)}</span>
              </li>
            ))}
          </ul>
        </QueryState>
      </div>
    </Card>
  );
}
