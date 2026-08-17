import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Card } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { Select } from "@/components/ui/Select";
import { QueryState } from "@/components/common/QueryState";
import { Pagination } from "@/components/common/Pagination";
import { TaskFormModal } from "@/features/tasks/TaskFormModal";
import { createTask, listTasks, updateTask } from "@/features/tasks/api";
import { useAuth } from "@/features/auth/AuthContext";
import { canWrite } from "@/lib/permissions";
import type { TaskPriority, TaskResponse, TaskStatus } from "@/types/tasks";

const PRIORITY_STYLES: Record<TaskPriority, string> = {
  low: "bg-slate-700 text-slate-300",
  medium: "bg-indigo-500/15 text-indigo-300",
  high: "bg-red-500/15 text-red-300",
};

const STATUS_STYLES: Record<TaskStatus, string> = {
  open: "bg-slate-700 text-slate-300",
  in_progress: "bg-indigo-500/15 text-indigo-300",
  done: "bg-emerald-500/15 text-emerald-300",
  cancelled: "bg-slate-700 text-slate-500",
};

const PAGE_SIZE = 20;

export function TasksPage() {
  const { me } = useAuth();
  const canManage = canWrite(me?.role);
  const queryClient = useQueryClient();

  const [page, setPage] = useState(1);
  const [status, setStatus] = useState<TaskStatus | "">("");
  const [priority, setPriority] = useState<TaskPriority | "">("");
  const [editing, setEditing] = useState<TaskResponse | undefined | null>(null);

  const { data, isLoading, isError, error } = useQuery({
    queryKey: ["tasks", { page, status, priority }],
    queryFn: () =>
      listTasks({
        page,
        page_size: PAGE_SIZE,
        status: status || undefined,
        priority: priority || undefined,
      }),
  });

  const invalidate = () => queryClient.invalidateQueries({ queryKey: ["tasks"] });

  const createMutation = useMutation({
    mutationFn: createTask,
    onSuccess: () => {
      invalidate();
      setEditing(null);
    },
  });

  const updateMutation = useMutation({
    mutationFn: ({ id, values }: { id: string; values: Parameters<typeof updateTask>[1] }) =>
      updateTask(id, values),
    onSuccess: () => {
      invalidate();
      setEditing(null);
    },
  });

  return (
    <div className="flex flex-col gap-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold text-slate-100">Tasks</h1>
          <p className="mt-1 text-sm text-slate-400">Track follow-ups and action items.</p>
        </div>
        {canManage && <Button onClick={() => setEditing(undefined)}>New Task</Button>}
      </div>

      <Card>
        <div className="mb-4 flex flex-wrap gap-3">
          <Select
            value={status}
            onChange={(e) => {
              setPage(1);
              setStatus(e.target.value as TaskStatus | "");
            }}
            className="max-w-xs"
          >
            <option value="">All statuses</option>
            <option value="open">Open</option>
            <option value="in_progress">In Progress</option>
            <option value="done">Done</option>
            <option value="cancelled">Cancelled</option>
          </Select>
          <Select
            value={priority}
            onChange={(e) => {
              setPage(1);
              setPriority(e.target.value as TaskPriority | "");
            }}
            className="max-w-xs"
          >
            <option value="">All priorities</option>
            <option value="low">Low</option>
            <option value="medium">Medium</option>
            <option value="high">High</option>
          </Select>
        </div>

        <QueryState
          isLoading={isLoading}
          isError={isError}
          error={error}
          isEmpty={!isLoading && !isError && (data?.items.length ?? 0) === 0}
          emptyMessage="No tasks match your filters."
        >
          <table className="w-full text-left text-sm">
            <thead>
              <tr className="border-b border-slate-800 text-xs uppercase tracking-wide text-slate-500">
                <th className="pb-2">Title</th>
                <th className="pb-2">Priority</th>
                <th className="pb-2">Status</th>
                <th className="pb-2">Due Date</th>
                {canManage && <th className="pb-2 text-right">Actions</th>}
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800">
              {data?.items.map((task) => (
                <tr key={task.id}>
                  <td className="py-2 text-slate-200">{task.title}</td>
                  <td className="py-2">
                    <span
                      className={`rounded-full px-2 py-0.5 text-xs capitalize ${PRIORITY_STYLES[task.priority]}`}
                    >
                      {task.priority}
                    </span>
                  </td>
                  <td className="py-2">
                    <span
                      className={`rounded-full px-2 py-0.5 text-xs capitalize ${STATUS_STYLES[task.status]}`}
                    >
                      {task.status.replace("_", " ")}
                    </span>
                  </td>
                  <td className="py-2 text-slate-400">
                    {task.due_date ? new Date(task.due_date).toLocaleDateString() : "—"}
                  </td>
                  {canManage && (
                    <td className="py-2 text-right">
                      <button
                        className="text-xs text-indigo-400 hover:text-indigo-300"
                        onClick={() => setEditing(task)}
                      >
                        Edit
                      </button>
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
        <TaskFormModal
          task={editing}
          onClose={() => setEditing(null)}
          onSubmit={async (values) => {
            const assignedTo = values.assignToMe ? me?.user.id : undefined;
            if (editing) {
              await updateMutation.mutateAsync({
                id: editing.id,
                values: {
                  title: values.title,
                  description: values.description || undefined,
                  priority: values.priority,
                  status: values.status,
                  due_date: values.due_date || undefined,
                  assigned_to: values.assignToMe ? assignedTo : null,
                },
              });
            } else {
              await createMutation.mutateAsync({
                title: values.title,
                description: values.description || undefined,
                priority: values.priority,
                due_date: values.due_date || undefined,
                assigned_to: assignedTo,
              });
            }
          }}
        />
      )}
    </div>
  );
}
