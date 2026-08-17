import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Button } from "@/components/ui/Button";
import { QueryState } from "@/components/common/QueryState";
import { createConversation, listConversations } from "@/features/copilot/api";

interface ConversationListProps {
  selectedId: string | null;
  onSelect: (id: string) => void;
}

export function ConversationList({ selectedId, onSelect }: ConversationListProps) {
  const queryClient = useQueryClient();

  const { data, isLoading, isError, error } = useQuery({
    queryKey: ["ai", "conversations"],
    queryFn: () => listConversations({ page: 1, page_size: 50 }),
  });

  const createMutation = useMutation({
    mutationFn: createConversation,
    onSuccess: (conversation) => {
      queryClient.invalidateQueries({ queryKey: ["ai", "conversations"] });
      onSelect(conversation.id);
    },
  });

  return (
    <div className="flex h-full flex-col gap-3">
      <Button
        variant="secondary"
        className="w-full"
        onClick={() => createMutation.mutate({})}
        isLoading={createMutation.isPending}
      >
        + New Conversation
      </Button>
      <div className="flex-1 overflow-y-auto">
        <QueryState
          isLoading={isLoading}
          isError={isError}
          error={error}
          isEmpty={!isLoading && !isError && (data?.items.length ?? 0) === 0}
          emptyMessage="No conversations yet."
        >
          <ul className="flex flex-col gap-1">
            {data?.items.map((conversation) => (
              <li key={conversation.id}>
                <button
                  onClick={() => onSelect(conversation.id)}
                  className={`w-full truncate rounded-md px-3 py-2 text-left text-sm ${
                    conversation.id === selectedId
                      ? "bg-indigo-500/15 text-indigo-300"
                      : "text-slate-300 hover:bg-slate-800"
                  }`}
                >
                  {conversation.title ?? "Untitled conversation"}
                </button>
              </li>
            ))}
          </ul>
        </QueryState>
      </div>
    </div>
  );
}
