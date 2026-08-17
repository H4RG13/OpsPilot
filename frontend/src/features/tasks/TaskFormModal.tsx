import { useState } from "react";
import type { FormEvent } from "react";
import { Modal } from "@/components/ui/Modal";
import { Input } from "@/components/ui/Input";
import { Select } from "@/components/ui/Select";
import { Button } from "@/components/ui/Button";
import { Alert } from "@/components/ui/Alert";
import { getErrorMessage } from "@/lib/errors";
import { useAuth } from "@/features/auth/AuthContext";
import type { TaskPriority, TaskResponse, TaskStatus } from "@/types/tasks";

interface TaskFormValues {
  title: string;
  description: string;
  priority: TaskPriority;
  status: TaskStatus;
  due_date: string;
  assignToMe: boolean;
}

interface TaskFormModalProps {
  task?: TaskResponse;
  onClose: () => void;
  onSubmit: (values: TaskFormValues) => Promise<void>;
}

export function TaskFormModal({ task, onClose, onSubmit }: TaskFormModalProps) {
  const { me } = useAuth();
  const [values, setValues] = useState<TaskFormValues>({
    title: task?.title ?? "",
    description: task?.description ?? "",
    priority: task?.priority ?? "medium",
    status: task?.status ?? "open",
    due_date: task?.due_date ?? "",
    assignToMe: task ? task.assigned_to === me?.user.id : false,
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
    <Modal title={task ? "Edit Task" : "New Task"} onClose={onClose}>
      <form onSubmit={handleSubmit} className="flex flex-col gap-4">
        {error && <Alert variant="error">{error}</Alert>}
        <Input
          label="Title"
          name="title"
          required
          value={values.title}
          onChange={(e) => setValues((v) => ({ ...v, title: e.target.value }))}
        />
        <Input
          label="Description"
          name="description"
          value={values.description}
          onChange={(e) => setValues((v) => ({ ...v, description: e.target.value }))}
        />
        <Select
          label="Priority"
          name="priority"
          value={values.priority}
          onChange={(e) => setValues((v) => ({ ...v, priority: e.target.value as TaskPriority }))}
        >
          <option value="low">Low</option>
          <option value="medium">Medium</option>
          <option value="high">High</option>
        </Select>
        {task && (
          <Select
            label="Status"
            name="status"
            value={values.status}
            onChange={(e) => setValues((v) => ({ ...v, status: e.target.value as TaskStatus }))}
          >
            <option value="open">Open</option>
            <option value="in_progress">In Progress</option>
            <option value="done">Done</option>
            <option value="cancelled">Cancelled</option>
          </Select>
        )}
        <Input
          label="Due Date"
          name="due_date"
          type="date"
          value={values.due_date}
          onChange={(e) => setValues((v) => ({ ...v, due_date: e.target.value }))}
        />
        <label className="flex items-center gap-2 text-sm text-slate-300">
          <input
            type="checkbox"
            checked={values.assignToMe}
            onChange={(e) => setValues((v) => ({ ...v, assignToMe: e.target.checked }))}
            className="h-4 w-4 rounded border-slate-700 bg-slate-900 text-indigo-500"
          />
          Assign to me
        </label>
        <div className="mt-2 flex justify-end gap-2">
          <Button type="button" variant="secondary" onClick={onClose} disabled={isSubmitting}>
            Cancel
          </Button>
          <Button type="submit" isLoading={isSubmitting}>
            {task ? "Save Changes" : "Create Task"}
          </Button>
        </div>
      </form>
    </Modal>
  );
}
