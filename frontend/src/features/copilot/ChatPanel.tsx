import { useState } from "react";
import type { FormEvent } from "react";
import { useMutation } from "@tanstack/react-query";
import { Card } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { Alert } from "@/components/ui/Alert";
import { StructuredAnswer } from "@/features/copilot/StructuredAnswer";
import { sendMessage } from "@/features/copilot/api";
import { getErrorMessage } from "@/lib/errors";
import type { ChatTurn } from "@/types/ai";

interface ChatPanelProps {
  conversationId: string;
}

export function ChatPanel({ conversationId }: ChatPanelProps) {
  const [turns, setTurns] = useState<Record<string, ChatTurn[]>>({});
  const [input, setInput] = useState("");
  const [allowAiActions, setAllowAiActions] = useState(false);

  const messages = turns[conversationId] ?? [];

  const mutation = useMutation({
    mutationFn: (content: string) =>
      sendMessage(conversationId, { content, allow_ai_actions: allowAiActions }),
  });

  function appendTurn(turn: ChatTurn) {
    setTurns((prev) => ({
      ...prev,
      [conversationId]: [...(prev[conversationId] ?? []), turn],
    }));
  }

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    const content = input.trim();
    if (!content) return;

    appendTurn({ id: crypto.randomUUID(), role: "user", content });
    setInput("");

    try {
      const answer = await mutation.mutateAsync(content);
      appendTurn({ id: crypto.randomUUID(), role: "assistant", content: answer.answer, answer });
    } catch {
      // Error is surfaced below via mutation.isError; nothing else to do here.
    }
  }

  return (
    <div className="flex h-full flex-col gap-4">
      <div className="flex-1 space-y-4 overflow-y-auto">
        {messages.length === 0 && (
          <p className="text-sm text-slate-500">
            Ask about revenue, orders, top products, or at-risk customers.
          </p>
        )}
        {messages.map((turn) =>
          turn.role === "user" ? (
            <div key={turn.id} className="flex justify-end">
              <div className="max-w-lg rounded-lg bg-indigo-500/15 px-4 py-2 text-sm text-indigo-100">
                {turn.content}
              </div>
            </div>
          ) : (
            <Card key={turn.id} className="max-w-2xl">
              {turn.answer ? <StructuredAnswer answer={turn.answer} /> : turn.content}
            </Card>
          )
        )}
        {mutation.isPending && <p className="text-sm text-slate-500">Thinking…</p>}
        {mutation.isError && <Alert variant="error">{getErrorMessage(mutation.error)}</Alert>}
      </div>

      <form onSubmit={handleSubmit} className="flex flex-col gap-2 border-t border-slate-800 pt-4">
        <label className="flex items-center gap-2 text-xs text-slate-400">
          <input
            type="checkbox"
            checked={allowAiActions}
            onChange={(e) => setAllowAiActions(e.target.checked)}
            className="h-4 w-4 rounded border-slate-700 bg-slate-900 text-indigo-500"
          />
          Allow the Copilot to create tasks on my behalf
        </label>
        <div className="flex gap-2">
          <textarea
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault();
                handleSubmit(e);
              }
            }}
            placeholder="Ask the Copilot a question…"
            rows={2}
            className="flex-1 resize-none rounded-md border border-slate-700 bg-slate-900 px-3 py-2 text-sm text-slate-100 placeholder:text-slate-500 focus:outline-none focus:ring-2 focus:ring-indigo-500/50"
          />
          <Button type="submit" isLoading={mutation.isPending} disabled={!input.trim()}>
            Send
          </Button>
        </div>
      </form>
    </div>
  );
}
