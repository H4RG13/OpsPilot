export type TaskPriority = "low" | "medium" | "high";
export type TaskStatus = "open" | "in_progress" | "done" | "cancelled";

export interface TaskResponse {
  id: string;
  created_by: string | null;
  assigned_to: string | null;
  title: string;
  description: string | null;
  priority: TaskPriority;
  status: TaskStatus;
  due_date: string | null;
  created_at: string;
}
