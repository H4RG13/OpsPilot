import { useState } from "react";
import type { FormEvent } from "react";
import { Modal } from "@/components/ui/Modal";
import { Input } from "@/components/ui/Input";
import { Button } from "@/components/ui/Button";
import { Alert } from "@/components/ui/Alert";
import { getErrorMessage } from "@/lib/errors";
import type { ProductResponse } from "@/types/products";

interface ProductFormValues {
  name: string;
  category: string;
  price: string;
  active: boolean;
}

interface ProductFormModalProps {
  product?: ProductResponse;
  onClose: () => void;
  onSubmit: (values: ProductFormValues) => Promise<void>;
}

export function ProductFormModal({ product, onClose, onSubmit }: ProductFormModalProps) {
  const [values, setValues] = useState<ProductFormValues>({
    name: product?.name ?? "",
    category: product?.category ?? "",
    price: product?.price ?? "",
    active: product?.active ?? true,
  });
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    setError(null);
    setIsSubmitting(true);
    try {
      await onSubmit(values);
    } catch (err) {
      setError(getErrorMessage(err));
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <Modal title={product ? "Edit Product" : "New Product"} onClose={onClose}>
      <form onSubmit={handleSubmit} className="flex flex-col gap-4">
        {error && <Alert variant="error">{error}</Alert>}
        <Input
          label="Name"
          name="name"
          required
          value={values.name}
          onChange={(e) => setValues((v) => ({ ...v, name: e.target.value }))}
        />
        <Input
          label="Category"
          name="category"
          required
          value={values.category}
          onChange={(e) => setValues((v) => ({ ...v, category: e.target.value }))}
        />
        <Input
          label="Price"
          name="price"
          type="number"
          min="0.01"
          step="0.01"
          required
          value={values.price}
          onChange={(e) => setValues((v) => ({ ...v, price: e.target.value }))}
        />
        <label className="flex items-center gap-2 text-sm text-slate-300">
          <input
            type="checkbox"
            checked={values.active}
            onChange={(e) => setValues((v) => ({ ...v, active: e.target.checked }))}
            className="h-4 w-4 rounded border-slate-700 bg-slate-900 text-indigo-500"
          />
          Active
        </label>
        <div className="mt-2 flex justify-end gap-2">
          <Button type="button" variant="secondary" onClick={onClose} disabled={isSubmitting}>
            Cancel
          </Button>
          <Button type="submit" isLoading={isSubmitting}>
            {product ? "Save Changes" : "Create Product"}
          </Button>
        </div>
      </form>
    </Modal>
  );
}
