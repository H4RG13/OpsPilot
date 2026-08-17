import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Card } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { Select } from "@/components/ui/Select";
import { QueryState } from "@/components/common/QueryState";
import { Pagination } from "@/components/common/Pagination";
import { ConfirmDialog } from "@/components/common/ConfirmDialog";
import { ProductFormModal } from "@/features/products/ProductFormModal";
import { createProduct, deleteProduct, listProducts, updateProduct } from "@/features/products/api";
import { useAuth } from "@/features/auth/AuthContext";
import { canWrite } from "@/lib/permissions";
import { formatCurrency } from "@/lib/format";
import type { ProductResponse } from "@/types/products";

const PAGE_SIZE = 20;

export function ProductsPage() {
  const { me } = useAuth();
  const canManage = canWrite(me?.role);
  const queryClient = useQueryClient();

  const [page, setPage] = useState(1);
  const [category, setCategory] = useState("");
  const [active, setActive] = useState<"" | "true" | "false">("");
  const [editing, setEditing] = useState<ProductResponse | undefined | null>(null);
  const [deleting, setDeleting] = useState<ProductResponse | null>(null);

  const { data, isLoading, isError, error } = useQuery({
    queryKey: ["products", { page, category, active }],
    queryFn: () =>
      listProducts({
        page,
        page_size: PAGE_SIZE,
        category: category || undefined,
        active: active === "" ? undefined : active === "true",
      }),
  });

  const invalidate = () => queryClient.invalidateQueries({ queryKey: ["products"] });

  const createMutation = useMutation({
    mutationFn: createProduct,
    onSuccess: () => {
      invalidate();
      setEditing(null);
    },
  });

  const updateMutation = useMutation({
    mutationFn: ({ id, values }: { id: string; values: Parameters<typeof updateProduct>[1] }) =>
      updateProduct(id, values),
    onSuccess: () => {
      invalidate();
      setEditing(null);
    },
  });

  const deleteMutation = useMutation({
    mutationFn: deleteProduct,
    onSuccess: () => {
      invalidate();
      setDeleting(null);
    },
  });

  return (
    <div className="flex flex-col gap-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold text-slate-100">Products</h1>
          <p className="mt-1 text-sm text-slate-400">Manage your product catalog.</p>
        </div>
        {canManage && <Button onClick={() => setEditing(undefined)}>New Product</Button>}
      </div>

      <Card>
        <div className="mb-4 flex flex-wrap gap-3">
          <Input
            placeholder="Filter by category…"
            value={category}
            onChange={(e) => {
              setPage(1);
              setCategory(e.target.value);
            }}
            className="max-w-xs"
          />
          <Select
            value={active}
            onChange={(e) => {
              setPage(1);
              setActive(e.target.value as "" | "true" | "false");
            }}
            className="max-w-xs"
          >
            <option value="">All products</option>
            <option value="true">Active only</option>
            <option value="false">Inactive only</option>
          </Select>
        </div>

        <QueryState
          isLoading={isLoading}
          isError={isError}
          error={error}
          isEmpty={!isLoading && !isError && (data?.items.length ?? 0) === 0}
          emptyMessage="No products match your filters."
        >
          <div className="overflow-x-auto">
          <table className="w-full text-left text-sm">
            <thead>
              <tr className="border-b border-slate-800 text-xs uppercase tracking-wide text-slate-500">
                <th className="pb-2">Name</th>
                <th className="pb-2">Category</th>
                <th className="pb-2">Price</th>
                <th className="pb-2">Status</th>
                {canManage && <th className="pb-2 text-right">Actions</th>}
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800">
              {data?.items.map((product) => (
                <tr key={product.id}>
                  <td className="py-2 text-slate-200">{product.name}</td>
                  <td className="py-2 text-slate-400">{product.category}</td>
                  <td className="py-2 text-slate-200">{formatCurrency(product.price)}</td>
                  <td className="py-2">
                    <span
                      className={`rounded-full px-2 py-0.5 text-xs ${
                        product.active
                          ? "bg-emerald-500/15 text-emerald-300"
                          : "bg-slate-700 text-slate-400"
                      }`}
                    >
                      {product.active ? "Active" : "Inactive"}
                    </span>
                  </td>
                  {canManage && (
                    <td className="py-2 text-right">
                      <div className="flex justify-end gap-3">
                        <button
                          className="text-xs text-indigo-400 hover:text-indigo-300"
                          onClick={() => setEditing(product)}
                        >
                          Edit
                        </button>
                        <button
                          className="text-xs text-red-400 hover:text-red-300"
                          onClick={() => setDeleting(product)}
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
          </div>
        </QueryState>

        {data && (
          <div className="mt-4">
            <Pagination page={data.page} pageSize={data.page_size} total={data.total} onPageChange={setPage} />
          </div>
        )}
      </Card>

      {editing !== null && (
        <ProductFormModal
          product={editing}
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
          title="Delete Product"
          message={`Are you sure you want to delete "${deleting.name}"? This cannot be undone.`}
          isConfirming={deleteMutation.isPending}
          onConfirm={() => deleteMutation.mutate(deleting.id)}
          onCancel={() => setDeleting(null)}
        />
      )}
    </div>
  );
}
