import { useState } from "react";
import { Card } from "@/components/ui/Card";
import { ConversationList } from "@/features/copilot/ConversationList";
import { ChatPanel } from "@/features/copilot/ChatPanel";

export function CopilotPage() {
  const [selectedId, setSelectedId] = useState<string | null>(null);

  return (
    <div className="flex h-[calc(100vh-8rem)] flex-col gap-6">
      <div>
        <h1 className="text-2xl font-semibold text-slate-100">AI Copilot</h1>
        <p className="mt-1 text-sm text-slate-400">
          Ask questions about your business data and get insights, recommendations, and suggested
          tasks.
        </p>
      </div>

      <div className="grid flex-1 grid-cols-1 gap-4 overflow-hidden lg:grid-cols-4">
        <Card className="overflow-hidden lg:col-span-1">
          <ConversationList selectedId={selectedId} onSelect={setSelectedId} />
        </Card>
        <Card className="overflow-hidden lg:col-span-3">
          {selectedId ? (
            <ChatPanel key={selectedId} conversationId={selectedId} />
          ) : (
            <p className="text-sm text-slate-500">
              Select a conversation or start a new one to begin chatting with the Copilot.
            </p>
          )}
        </Card>
      </div>
    </div>
  );
}
