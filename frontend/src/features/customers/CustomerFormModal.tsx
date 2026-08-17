import { useState } from "react";
import type { FormEvent } from "react";
import { Modal } from "@/components/ui/Modal";
import { Input } from "@/components/ui/Input";
import { Select } from "@/components/ui/Select";
import { Button } from "@/components/ui/Button";
import { Alert } from "@/components/ui/Alert";
import { getErrorMessage } from "@/lib/errors";
import type { CustomerResponse, CustomerStatus } from "@/types/customers";

interface CustomerFormValues {
  name: string;
  email: string;
  status: CustomerStatus;
  lifetime_value: string;
}

interface CustomerFormModalProps {
  customer?: CustomerResponse;
  onClose: () => void;
  onSubmit: (values: CustomerFormValues) => Promise<void>;
}

export function CustomerFormModal({ customer, onClose, onSubmit }: CustomerFormModalProps) {
  const [values, setValues] = useState<CustomerFormValues>({
    name: customer?.name ?? "",
    email: customer?.email ?? "",
    status: customer?.status ?? "active",
    lifetime_value: customer?.lifetime_value ?? "0",
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
    <Modal title={customer ? "Edit Customer" : "New Customer"} onClose={onClose}>
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
          label="Email"
          name="email"
          type="email"
          required
          value={values.email}
          onChange={(e) => setValues((v) => ({ ...v, email: e.target.value }))}
        />
        <Select
          label="Status"
          name="status"
          value={values.status}
          onChange={(e) => setValues((v) => ({ ...v, status: e.target.value as CustomerStatus }))}
        >
          <option value="active">Active</option>
          <option value="inactive">Inactive</option>
          <option value="at_risk">At Risk</option>
        </Select>
        <Input
          label="Lifetime Value"
          name="lifetime_value"
          type="number"
          min="0"
          step="0.01"
          value={values.lifetime_value}
          onChange={(e) => setValues((v) => ({ ...v, lifetime_value: e.target.value }))}
        />
        <div className="mt-2 flex justify-end gap-2">
          <Button type="button" variant="secondary" onClick={onClose} disabled={isSubmitting}>
            Cancel
          </Button>
          <Button type="submit" isLoading={isSubmitting}>
            {customer ? "Save Changes" : "Create Customer"}
          </Button>
        </div>
      </form>
    </Modal>
  );
}
