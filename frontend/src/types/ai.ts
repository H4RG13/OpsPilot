export type InsightSeverity = "low" | "medium" | "high";

export interface Insight {
  title: string;
  severity: InsightSeverity;
  evidence: string;
}

export interface SuggestedTask {
  title: string;
  priority: "low" | "medium" | "high";
}

export interface StructuredAIAnswer {
  answer: string;
  insights: Insight[];
  recommendations: string[];
  suggested_tasks: SuggestedTask[];
}

export interface ConversationResponse {
  id: string;
  title: string | null;
  created_at: string;
}

export interface ConversationCreatePayload {
  title?: string;
}

export interface MessageCreatePayload {
  content: string;
  allow_ai_actions?: boolean;
}

/** Client-side only — the backend has no endpoint to fetch a conversation's
 * past messages, so chat history exists only for the current browser session. */
export interface ChatTurn {
  id: string;
  role: "user" | "assistant";
  content: string;
  answer?: StructuredAIAnswer;
}
