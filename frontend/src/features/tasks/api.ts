import { api } from "@/lib/api";
import type { Page } from "@/types/pagination";
import type {
  TaskCreatePayload,
  TaskPriority,
  TaskResponse,
  TaskStatus,
  TaskUpdatePayload,
} from "@/types/tasks";

export interface TaskListParams {
  page?: number;
  page_size?: number;
  status?: TaskStatus;
  priority?: TaskPriority;
}

export async function listTasks(params: TaskListParams): Promise<Page<TaskResponse>> {
  const { data } = await api.get<Page<TaskResponse>>("/tasks", { params });
  return data;
}

export async function createTask(payload: TaskCreatePayload): Promise<TaskResponse> {
  const { data } = await api.post<TaskResponse>("/tasks", payload);
  return data;
}

export async function updateTask(id: string, payload: TaskUpdatePayload): Promise<TaskResponse> {
  const { data } = await api.patch<TaskResponse>(`/tasks/${id}`, payload);
  return data;
}
