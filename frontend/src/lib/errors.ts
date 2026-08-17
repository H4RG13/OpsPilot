import { isAxiosError } from "axios";

interface ApiErrorBody {
  error?: {
    code?: string;
    message?: string;
  };
}

/** Extracts a user-displayable message from the backend's error envelope
 * ({"error": {"code", "message", "request_id"}}), falling back gracefully
 * for network errors or anything that doesn't match that shape. */
export function getErrorMessage(error: unknown): string {
  if (isAxiosError<ApiErrorBody>(error)) {
    const message = error.response?.data?.error?.message;
    if (message) return message;
    if (error.response?.status === 429) return "Too many requests. Please try again shortly.";
    if (!error.response) return "Could not reach the server. Check your connection.";
  }
  if (error instanceof Error) return error.message;
  return "Something went wrong. Please try again.";
}

export function getErrorCode(error: unknown): string | undefined {
  if (isAxiosError<ApiErrorBody>(error)) {
    return error.response?.data?.error?.code;
  }
  return undefined;
}
