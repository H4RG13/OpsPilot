import { useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { Button } from "@/components/ui/Button";
import { createTask } from "@/features/tasks/api";
import type { InsightSeverity, StructuredAIAnswer, SuggestedTask } from "@/types/ai";

const SEVERITY_STYLES: Record<InsightSeverity, string> = {
  low: "bg-slate-700 text-slate-300",
  medium: "bg-amber-500/15 text-amber-300",
  high: "bg-red-500/15 text-red-300",
};

function SuggestedTaskRow({ task }: { task: SuggestedTask }) {
  const [created, setCreated] = useState(false);
  const mutation = useMutation({
    mutationFn: () => createTask({ title: task.title, priority: task.priority }),
    onSuccess: () => setCreated(true),
  });

  return (
    <li className="flex items-center justify-between gap-3 rounded-md border border-slate-800 px-3 py-2">
      <span className="text-sm text-slate-200">{task.title}</span>
      <div className="flex items-center gap-2">
        <span
          className={`rounded-full px-2 py-0.5 text-xs capitalize ${SEVERITY_STYLES[task.priority]}`}
        >
          {task.priority}
        </span>
        <Button
          variant="secondary"
          className="px-2 py-1 text-xs"
          onClick={() => mutation.mutate()}
          isLoading={mutation.isPending}
          disabled={created}
        >
          {created ? "Created" : "Create Task"}
        </Button>
      </div>
    </li>
  );
}

export function StructuredAnswer({ answer }: { answer: StructuredAIAnswer }) {
  return (
    <div className="flex flex-col gap-4">
      <p className="whitespace-pre-wrap text-sm text-slate-100">{answer.answer}</p>

      {answer.insights.length > 0 && (
        <div>
          <h4 className="mb-2 text-xs font-semibold uppercase tracking-wide text-slate-500">
            Insights
          </h4>
          <ul className="flex flex-col gap-2">
            {answer.insights.map((insight, index) => (
              <li key={index} className="rounded-md border border-slate-800 px-3 py-2">
                <div className="flex items-center justify-between">
                  <span className="text-sm font-medium text-slate-200">{insight.title}</span>
                  <span
                    className={`rounded-full px-2 py-0.5 text-xs capitalize ${SEVERITY_STYLES[insight.severity]}`}
                  >
                    {insight.severity}
                  </span>
                </div>
                <p className="mt-1 text-xs text-slate-400">{insight.evidence}</p>
              </li>
            ))}
          </ul>
        </div>
      )}

      {answer.recommendations.length > 0 && (
        <div>
          <h4 className="mb-2 text-xs font-semibold uppercase tracking-wide text-slate-500">
            Recommendations
          </h4>
          <ul className="list-inside list-disc space-y-1 text-sm text-slate-300">
            {answer.recommendations.map((recommendation, index) => (
              <li key={index}>{recommendation}</li>
            ))}
          </ul>
        </div>
      )}

      {answer.suggested_tasks.length > 0 && (
        <div>
          <h4 className="mb-2 text-xs font-semibold uppercase tracking-wide text-slate-500">
            Suggested Tasks
          </h4>
          <ul className="flex flex-col gap-2">
            {answer.suggested_tasks.map((task, index) => (
              <SuggestedTaskRow key={index} task={task} />
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
