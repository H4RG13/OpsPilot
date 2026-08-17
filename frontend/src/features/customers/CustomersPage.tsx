import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Card } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { Select } from "@/components/ui/Select";
import { QueryState } from "@/components/common/QueryState";
import { Pagination } from "@/components/common/Pagination";
import { ConfirmDialog } from "@/components/common/ConfirmDialog";
import { CustomerFormModal } from "@/features/customers/CustomerFormModal";
import { createCustomer, deleteCustomer, listCustomers, updateCustomer } from "@/features/customers/api";
import { useAuth } from "@/features/auth/AuthContext";
import { canWrite } from "@/lib/permissions";
import { formatCurrency } from "@/lib/format";
import type { CustomerResponse, CustomerStatus } from "@/types/customers";

const STATUS_STYLES: Record<CustomerStatus, string> = {
  active: "bg-emerald-500/15 text-emerald-300",
  inactive: "bg-slate-700 text-slate-400",
  at_risk: "bg-amber-500/15 text-amber-300",
};

const PAGE_SIZE = 20;

export function CustomersPage() {
  const { me } = useAuth();
  const canManage = canWrite(me?.role);
  const queryClient = useQueryClient();

  const [page, setPage] = useState(1);
  const [search, setSearch] = useState("");
  const [status, setStatus] = useState<CustomerStatus | "">("");
  const [editing, setEditing] = useState<CustomerResponse | undefined | null>(null);
  const [deleting, setDeleting] = useState<CustomerResponse | null>(null);

  const { data, isLoading, isError, error } = useQuery({
    queryKey: ["customers", { page, search, status }],
    queryFn: () =>
      listCustomers({
        page,
        page_size: PAGE_SIZE,
        search: search || undefined,
        status: status || undefined,
      }),
  });

  const invalidate = () => queryClient.invalidateQueries({ queryKey: ["customers"] });

  const createMutation = useMutation({
    mutationFn: createCustomer,
    onSuccess: () => {
      invalidate();
      setEditing(null);
    },
  });

  const updateMutation = useMutation({
    mutationFn: ({ id, values }: { id: string; values: Parameters<typeof updateCustomer>[1] }) =>
      updateCustomer(id, values),
    onSuccess: () => {
      invalidate();
      setEditing(null);
    },
  });

  const deleteMutation = useMutation({
    mutationFn: deleteCustomer,
    onSuccess: () => {
      invalidate();
      setDeleting(null);
    },
  });

  return (
    <div className="flex flex-col gap-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold text-slate-100">Customers</h1>
          <p className="mt-1 text-sm text-slate-400">Manage your customer records.</p>
        </div>
        {canManage && <Button onClick={() => setEditing(undefined)}>New Customer</Button>}
      </div>

      <Card>
        <div className="mb-4 flex flex-wrap gap-3">
          <Input
            placeholder="Search by name or email…"
            value={search}
            onChange={(e) => {
              setPage(1);
              setSearch(e.target.value);
            }}
            className="max-w-xs"
          />
          <Select
            value={status}
            onChange={(e) => {
              setPage(1);
              setStatus(e.target.value as CustomerStatus | "");
            }}
            className="max-w-xs"
          >
            <option value="">All statuses</option>
            <option value="active">Active</option>
            <option value="inactive">Inactive</option>
            <option value="at_risk">At Risk</option>
          </Select>
        </div>

        <QueryState
          isLoading={isLoading}
          isError={isError}
          error={error}
          isEmpty={!isLoading && !isError && (data?.items.length ?? 0) === 0}
          emptyMessage="No customers match your filters."
        >
          <table className="w-full text-left text-sm">
            <thead>
              <tr className="border-b border-slate-800 text-xs uppercase tracking-wide text-slate-500">
                <th className="pb-2">Name</th>
                <th className="pb-2">Email</th>
                <th className="pb-2">Status</th>
                <th className="pb-2">Lifetime Value</th>
                {canManage && <th className="pb-2 text-right">Actions</th>}
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800">
              {data?.items.map((customer) => (
                <tr key={customer.id}>
                  <td className="py-2 text-slate-200">{customer.name}</td>
                  <td className="py-2 text-slate-400">{customer.email}</td>
                  <td className="py-2">
                    <span
                      className={`rounded-full px-2 py-0.5 text-xs capitalize ${STATUS_STYLES[customer.status]}`}
                    >
                      {customer.status.replace("_", " ")}
                    </span>
                  </td>
                  <td className="py-2 text-slate-200">{formatCurrency(customer.lifetime_value)}</td>
                  {canManage && (
                    <td className="py-2 text-right">
                      <div className="flex justify-end gap-3">
                        <button
                          className="text-xs text-indigo-400 hover:text-indigo-300"
                          onClick={() => setEditing(customer)}
                        >
                          Edit
                        </button>
                        <button
                          className="text-xs text-red-400 hover:text-red-300"
                          onClick={() => setDeleting(customer)}
                        >
                          Delete
                        </button>
                      </div>
                    </td>
                  )}
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

      {editing !== null && (
        <CustomerFormModal
          customer={editing}
          onClose={() => setEditing(null)}
          onSubmit={async (values) => {
            if (editing) {
              await updateMutation.mutateAsync({ id: editing.id, values });
            } else {
              await createMutation.mutateAsync(values);
            }
          }}
        />
      )}

      {deleting && (
        <ConfirmDialog
          title="Delete Customer"
          message={`Are you sure you want to delete "${deleting.name}"? This cannot be undone.`}
          isConfirming={deleteMutation.isPending}
          onConfirm={() => deleteMutation.mutate(deleting.id)}
          onCancel={() => setDeleting(null)}
        />
      )}
    </div>
  );
}
