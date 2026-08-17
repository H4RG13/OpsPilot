import { useState } from "react";
import type { FormEvent } from "react";
import { useQuery } from "@tanstack/react-query";
import { Modal } from "@/components/ui/Modal";
import { Select } from "@/components/ui/Select";
import { Input } from "@/components/ui/Input";
import { Button } from "@/components/ui/Button";
import { Alert } from "@/components/ui/Alert";
import { getErrorMessage } from "@/lib/errors";
import { formatCurrency } from "@/lib/format";
import { listCustomers } from "@/features/customers/api";
import { listProducts } from "@/features/products/api";
import type { OrderCreatePayload, OrderItemInput } from "@/types/orders";

interface OrderFormModalProps {
  onClose: () => void;
  onSubmit: (payload: OrderCreatePayload) => Promise<unknown>;
}

interface ItemRow {
  product_id: string;
  quantity: string;
}

export function OrderFormModal({ onClose, onSubmit }: OrderFormModalProps) {
  const { data: customers } = useQuery({
    queryKey: ["customers", "picker"],
    queryFn: () => listCustomers({ page: 1, page_size: 100 }),
  });
  const { data: products } = useQuery({
    queryKey: ["products", "picker"],
    queryFn: () => listProducts({ page: 1, page_size: 100 }),
  });

  const [customerId, setCustomerId] = useState("");
  const [items, setItems] = useState<ItemRow[]>([{ product_id: "", quantity: "1" }]);
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const productsById = new Map((products?.items ?? []).map((p) => [p.id, p]));
  const estimatedTotal = items.reduce((sum, item) => {
    const product = productsById.get(item.product_id);
    const quantity = Number(item.quantity) || 0;
    return sum + (product ? Number(product.price) * quantity : 0);
  }, 0);

  function updateItem(index: number, patch: Partial<ItemRow>) {
    setItems((rows) => rows.map((row, i) => (i === index ? { ...row, ...patch } : row)));
  }

  function addItem() {
    setItems((rows) => [...rows, { product_id: "", quantity: "1" }]);
  }

  function removeItem(index: number) {
    setItems((rows) => rows.filter((_, i) => i !== index));
  }

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    setError(null);

    if (!customerId) {
      setError("Please select a customer.");
      return;
    }
    const orderItems: OrderItemInput[] = items
      .filter((row) => row.product_id)
      .map((row) => ({ product_id: row.product_id, quantity: Math.max(1, Number(row.quantity) || 1) }));
    if (orderItems.length === 0) {
      setError("Please add at least one product.");
      return;
    }

    setIsSubmitting(true);
    try {
      await onSubmit({ customer_id: customerId, items: orderItems });
    } catch (err) {
      setError(getErrorMessage(err));
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <Modal title="New Order" onClose={onClose}>
      <form onSubmit={handleSubmit} className="flex flex-col gap-4">
        {error && <Alert variant="error">{error}</Alert>}

        <Select label="Customer" value={customerId} onChange={(e) => setCustomerId(e.target.value)}>
          <option value="">Select a customer…</option>
          {customers?.items.map((customer) => (
            <option key={customer.id} value={customer.id}>
              {customer.name}
            </option>
          ))}
        </Select>

        <div className="flex flex-col gap-2">
          <span className="text-sm font-medium text-slate-300">Items</span>
          {items.map((row, index) => (
            <div key={index} className="flex gap-2">
              <Select
                value={row.product_id}
                onChange={(e) => updateItem(index, { product_id: e.target.value })}
                className="flex-1"
              >
                <option value="">Select a product…</option>
                {products?.items.map((product) => (
                  <option key={product.id} value={product.id}>
                    {product.name} ({formatCurrency(product.price)})
                  </option>
                ))}
              </Select>
              <Input
                type="number"
                min="1"
                step="1"
                value={row.quantity}
                onChange={(e) => updateItem(index, { quantity: e.target.value })}
                className="w-20"
              />
              <Button
                type="button"
                variant="ghost"
                onClick={() => removeItem(index)}
                disabled={items.length === 1}
              >
                ✕
              </Button>
            </div>
          ))}
          <Button type="button" variant="secondary" onClick={addItem} className="self-start text-xs">
            + Add item
          </Button>
        </div>

        <p className="text-sm text-slate-400">
          Estimated total: <span className="text-slate-200">{formatCurrency(estimatedTotal)}</span>
          <span className="ml-1 text-xs text-slate-500">(server computes the final total)</span>
        </p>

        <div className="mt-2 flex justify-end gap-2">
          <Button type="button" variant="secondary" onClick={onClose} disabled={isSubmitting}>
            Cancel
          </Button>
          <Button type="submit" isLoading={isSubmitting}>
            Create Order
          </Button>
        </div>
      </form>
    </Modal>
  );
}
