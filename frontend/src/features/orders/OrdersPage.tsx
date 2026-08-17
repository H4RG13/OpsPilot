import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Card } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { Select } from "@/components/ui/Select";
import { QueryState } from "@/components/common/QueryState";
import { Pagination } from "@/components/common/Pagination";
import { OrderFormModal } from "@/features/orders/OrderFormModal";
import { OrderDetailModal } from "@/features/orders/OrderDetailModal";
import { createOrder, listOrders, updateOrderStatus } from "@/features/orders/api";
import { listCustomers } from "@/features/customers/api";
import { listProducts } from "@/features/products/api";
import { useAuth } from "@/features/auth/AuthContext";
import { canWrite } from "@/lib/permissions";
import { formatCurrency } from "@/lib/format";
import type { OrderResponse, OrderStatus } from "@/types/orders";

const STATUS_STYLES: Record<OrderStatus, string> = {
  pending: "bg-amber-500/15 text-amber-300",
  completed: "bg-emerald-500/15 text-emerald-300",
  cancelled: "bg-slate-700 text-slate-400",
};

const STATUS_OPTIONS: OrderStatus[] = ["pending", "completed", "cancelled"];
const PAGE_SIZE = 20;

export function OrdersPage() {
  const { me } = useAuth();
  const canManage = canWrite(me?.role);
  const queryClient = useQueryClient();

  const [page, setPage] = useState(1);
  const [status, setStatus] = useState<OrderStatus | "">("");
  const [isCreating, setIsCreating] = useState(false);
  const [viewing, setViewing] = useState<OrderResponse | null>(null);

  const { data, isLoading, isError, error } = useQuery({
    queryKey: ["orders", { page, status }],
    queryFn: () => listOrders({ page, page_size: PAGE_SIZE, status: status || undefined }),
  });

  const { data: customers } = useQuery({
    queryKey: ["customers", "picker"],
    queryFn: () => listCustomers({ page: 1, page_size: 100 }),
  });
  const { data: products } = useQuery({
    queryKey: ["products", "picker"],
    queryFn: () => listProducts({ page: 1, page_size: 100 }),
  });
  const customersById = new Map((customers?.items ?? []).map((c) => [c.id, c]));
  const productsById = new Map((products?.items ?? []).map((p) => [p.id, p]));

  const invalidate = () => queryClient.invalidateQueries({ queryKey: ["orders"] });

  const createMutation = useMutation({
    mutationFn: createOrder,
    onSuccess: () => {
      invalidate();
      setIsCreating(false);
    },
  });

  const statusMutation = useMutation({
    mutationFn: ({ id, status: next }: { id: string; status: OrderStatus }) =>
      updateOrderStatus(id, next),
    onSuccess: invalidate,
  });

  return (
    <div className="flex flex-col gap-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold text-slate-100">Orders</h1>
          <p className="mt-1 text-sm text-slate-400">Track and manage customer orders.</p>
        </div>
        {canManage && <Button onClick={() => setIsCreating(true)}>New Order</Button>}
      </div>

      <Card>
        <div className="mb-4 flex flex-wrap gap-3">
          <Select
            value={status}
            onChange={(e) => {
              setPage(1);
              setStatus(e.target.value as OrderStatus | "");
            }}
            className="max-w-xs"
          >
            <option value="">All statuses</option>
            <option value="pending">Pending</option>
            <option value="completed">Completed</option>
            <option value="cancelled">Cancelled</option>
          </Select>
        </div>

        <QueryState
          isLoading={isLoading}
          isError={isError}
          error={error}
          isEmpty={!isLoading && !isError && (data?.items.length ?? 0) === 0}
          emptyMessage="No orders match your filters."
        >
          <table className="w-full text-left text-sm">
            <thead>
              <tr className="border-b border-slate-800 text-xs uppercase tracking-wide text-slate-500">
                <th className="pb-2">Customer</th>
                <th className="pb-2">Date</th>
                <th className="pb-2">Status</th>
                <th className="pb-2">Total</th>
                <th className="pb-2 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800">
              {data?.items.map((order) => (
                <tr key={order.id}>
                  <td className="py-2 text-slate-200">
                    {customersById.get(order.customer_id)?.name ?? "Unknown customer"}
                  </td>
                  <td className="py-2 text-slate-400">
                    {new Date(order.ordered_at).toLocaleDateString()}
                  </td>
                  <td className="py-2">
                    {canManage ? (
                      <Select
                        value={order.status}
                        onChange={(e) =>
                          statusMutation.mutate({ id: order.id, status: e.target.value as OrderStatus })
                        }
                        className="py-1 text-xs"
                      >
                        {STATUS_OPTIONS.map((option) => (
                          <option key={option} value={option}>
                            {option}
                          </option>
                        ))}
                      </Select>
                    ) : (
                      <span
                        className={`rounded-full px-2 py-0.5 text-xs capitalize ${STATUS_STYLES[order.status]}`}
                      >
                        {order.status}
                      </span>
                    )}
                  </td>
                  <td className="py-2 text-slate-200">{formatCurrency(order.total_amount)}</td>
                  <td className="py-2 text-right">
                    <button
                      className="text-xs text-indigo-400 hover:text-indigo-300"
                      onClick={() => setViewing(order)}
                    >
                      View
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </QueryState>

        {data && (
          <div className="mt-4">
            <Pagination page={data.page} pageSize={data.page_size} total={data.total} onPageChange={setPage} />
          </div>
        )}
      </Card>

      {isCreating && (
        <OrderFormModal
          onClose={() => setIsCreating(false)}
          onSubmit={(payload) => createMutation.mutateAsync(payload)}
        />
      )}

      {viewing && (
        <OrderDetailModal order={viewing} productsById={productsById} onClose={() => setViewing(null)} />
      )}
    </div>
  );
}
