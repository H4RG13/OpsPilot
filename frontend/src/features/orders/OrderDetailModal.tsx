import { Modal } from "@/components/ui/Modal";
import { formatCurrency } from "@/lib/format";
import type { OrderResponse } from "@/types/orders";
import type { ProductResponse } from "@/types/products";

interface OrderDetailModalProps {
  order: OrderResponse;
  productsById: Map<string, ProductResponse>;
  onClose: () => void;
}

export function OrderDetailModal({ order, productsById, onClose }: OrderDetailModalProps) {
  return (
    <Modal title="Order Details" onClose={onClose}>
      <div className="flex flex-col gap-4">
        <p className="text-xs text-slate-500">
          Placed {new Date(order.ordered_at).toLocaleString()}
        </p>
        <table className="w-full text-left text-sm">
          <thead>
            <tr className="border-b border-slate-800 text-xs uppercase tracking-wide text-slate-500">
              <th className="pb-2">Product</th>
              <th className="pb-2">Qty</th>
              <th className="pb-2">Unit Price</th>
              <th className="pb-2 text-right">Subtotal</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-800">
            {order.items.map((item) => (
              <tr key={item.id}>
                <td className="py-2 text-slate-200">
                  {productsById.get(item.product_id)?.name ?? "Unknown product"}
                </td>
                <td className="py-2 text-slate-400">{item.quantity}</td>
                <td className="py-2 text-slate-400">{formatCurrency(item.unit_price)}</td>
                <td className="py-2 text-right text-slate-200">{formatCurrency(item.subtotal)}</td>
              </tr>
            ))}
          </tbody>
        </table>
        <div className="flex justify-end border-t border-slate-800 pt-3 text-sm font-semibold text-slate-100">
          Total: {formatCurrency(order.total_amount)}
        </div>
      </div>
    </Modal>
  );
}
