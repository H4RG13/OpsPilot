import { describe, expect, it, vi } from "vitest";
import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { renderWithProviders } from "@/test/test-utils";
import { StructuredAnswer } from "@/features/copilot/StructuredAnswer";
import { createTask } from "@/features/tasks/api";
import type { StructuredAIAnswer } from "@/types/ai";

vi.mock("@/features/tasks/api", () => ({
  createTask: vi.fn(),
}));

const mockedCreateTask = vi.mocked(createTask);

const answer: StructuredAIAnswer = {
  answer: "Revenue is up this month.",
  insights: [{ title: "Top-selling product", severity: "high", evidence: "Gadget led sales." }],
  recommendations: ["Promote the Gadget further."],
  suggested_tasks: [{ title: "Launch a Gadget promo", priority: "high" }],
};

describe("StructuredAnswer", () => {
  it("renders the answer text, insights, recommendations, and suggested tasks", () => {
    renderWithProviders(<StructuredAnswer answer={answer} />);

    expect(screen.getByText("Revenue is up this month.")).toBeInTheDocument();
    expect(screen.getByText("Top-selling product")).toBeInTheDocument();
    expect(screen.getByText("Gadget led sales.")).toBeInTheDocument();
    expect(screen.getByText("Promote the Gadget further.")).toBeInTheDocument();
    expect(screen.getByText("Launch a Gadget promo")).toBeInTheDocument();
  });

  it("creates a real task from a suggestion and marks it as created", async () => {
    mockedCreateTask.mockResolvedValue({
      id: "task-1",
      created_by: null,
      assigned_to: null,
      title: "Launch a Gadget promo",
      description: null,
      priority: "high",
      status: "open",
      due_date: null,
      created_at: "2026-01-01T00:00:00Z",
    });

    renderWithProviders(<StructuredAnswer answer={answer} />);

    await userEvent.click(screen.getByRole("button", { name: "Create Task" }));

    expect(mockedCreateTask).toHaveBeenCalledWith({
      title: "Launch a Gadget promo",
      priority: "high",
    });
    expect(await screen.findByRole("button", { name: "Created" })).toBeDisabled();
  });
});
