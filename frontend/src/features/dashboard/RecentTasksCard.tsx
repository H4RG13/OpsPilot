import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { Card } from "@/components/ui/Card";
import { QueryState } from "@/components/common/QueryState";
import { getRecentTasks } from "@/features/dashboard/api";
import type { TaskPriority } from "@/types/tasks";

const PRIORITY_STYLES: Record<TaskPriority, string> = {
  low: "bg-slate-700 text-slate-300",
  medium: "bg-indigo-500/15 text-indigo-300",
  high: "bg-red-500/15 text-red-300",
};

export function RecentTasksCard() {
  const { data, isLoading, isError, error } = useQuery({
    queryKey: ["tasks", "recent"],
    queryFn: () => getRecentTasks(5),
  });

  return (
    <Card>
      <div className="flex items-center justify-between">
        <h2 className="text-sm font-semibold text-slate-200">Recent Tasks</h2>
        <Link to="/tasks" className="text-xs text-indigo-400 hover:text-indigo-300">
          View all
        </Link>
      </div>
      <div className="mt-4">
        <QueryState
          isLoading={isLoading}
          isError={isError}
          error={error}
          isEmpty={!isLoading && !isError && (data?.items.length ?? 0) === 0}
          emptyMessage="No tasks yet."
        >
          <ul className="divide-y divide-slate-800">
            {data?.items.map((task) => (
              <li key={task.id} className="flex items-center justify-between py-2 text-sm">
                <span className="truncate text-slate-200">{task.title}</span>
                <span
                  className={`ml-2 shrink-0 rounded-full px-2 py-0.5 text-xs capitalize ${PRIORITY_STYLES[task.priority]}`}
                >
                  {task.priority}
                </span>
              </li>
            ))}
          </ul>
        </QueryState>
      </div>
    </Card>
  );
}
