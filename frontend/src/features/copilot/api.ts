import { api } from "@/lib/api";
import type { Page } from "@/types/pagination";
import type {
  ConversationCreatePayload,
  ConversationResponse,
  MessageCreatePayload,
  StructuredAIAnswer,
} from "@/types/ai";

export interface ConversationListParams {
  page?: number;
  page_size?: number;
}

export async function listConversations(
  params: ConversationListParams
): Promise<Page<ConversationResponse>> {
  const { data } = await api.get<Page<ConversationResponse>>("/ai/conversations", { params });
  return data;
}

export async function createConversation(
  payload: ConversationCreatePayload
): Promise<ConversationResponse> {
  const { data } = await api.post<ConversationResponse>("/ai/conversations", payload);
  return data;
}

export async function sendMessage(
  conversationId: string,
  payload: MessageCreatePayload
): Promise<StructuredAIAnswer> {
  const { data } = await api.post<StructuredAIAnswer>(
    `/ai/conversations/${conversationId}/messages`,
    payload
  );
  return data;
}
