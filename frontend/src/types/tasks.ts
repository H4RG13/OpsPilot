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

export interface TaskCreatePayload {
  title: string;
  description?: string;
  priority?: TaskPriority;
  assigned_to?: string;
  due_date?: string;
}

export interface TaskUpdatePayload {
  title?: string;
  description?: string;
  priority?: TaskPriority;
  status?: TaskStatus;
  assigned_to?: string | null;
  due_date?: string;
}
