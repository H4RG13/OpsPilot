import { describe, expect, it, vi } from "vitest";
import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { renderWithProviders } from "@/test/test-utils";
import { ChatPanel } from "@/features/copilot/ChatPanel";
import { sendMessage } from "@/features/copilot/api";
import type { StructuredAIAnswer } from "@/types/ai";

vi.mock("@/features/copilot/api", () => ({
  sendMessage: vi.fn(),
}));

const mockedSendMessage = vi.mocked(sendMessage);

const answer: StructuredAIAnswer = {
  answer: "Here is your answer.",
  insights: [],
  recommendations: [],
  suggested_tasks: [],
};

describe("ChatPanel", () => {
  it("sends a message with allow_ai_actions false by default", async () => {
    mockedSendMessage.mockResolvedValue(answer);
    renderWithProviders(<ChatPanel conversationId="conv-1" />);

    await userEvent.type(
      screen.getByPlaceholderText("Ask the Copilot a question…"),
      "What is our revenue?"
    );
    await userEvent.click(screen.getByRole("button", { name: "Send" }));

    expect(mockedSendMessage).toHaveBeenCalledWith("conv-1", {
      content: "What is our revenue?",
      allow_ai_actions: false,
    });
    expect(await screen.findByText("Here is your answer.")).toBeInTheDocument();
  });

  it("sends allow_ai_actions true once the toggle is checked", async () => {
    mockedSendMessage.mockResolvedValue(answer);
    renderWithProviders(<ChatPanel conversationId="conv-2" />);

    await userEvent.click(
      screen.getByLabelText("Allow the Copilot to create tasks on my behalf")
    );
    await userEvent.type(
      screen.getByPlaceholderText("Ask the Copilot a question…"),
      "Create a follow-up task."
    );
    await userEvent.click(screen.getByRole("button", { name: "Send" }));

    expect(mockedSendMessage).toHaveBeenCalledWith("conv-2", {
      content: "Create a follow-up task.",
      allow_ai_actions: true,
    });
  });
});
