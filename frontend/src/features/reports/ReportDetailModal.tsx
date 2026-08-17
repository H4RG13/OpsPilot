import { Modal } from "@/components/ui/Modal";
import { Alert } from "@/components/ui/Alert";
import { StructuredAnswer } from "@/features/copilot/StructuredAnswer";
import type { StructuredAIAnswer } from "@/types/ai";
import type { ReportResponse } from "@/types/reports";

function parseSummary(summary: string | null): StructuredAIAnswer | null {
  if (!summary) return null;
  try {
    return JSON.parse(summary) as StructuredAIAnswer;
  } catch {
    return null;
  }
}

export function ReportDetailModal({
  report,
  onClose,
}: {
  report: ReportResponse;
  onClose: () => void;
}) {
  const summary = parseSummary(report.summary);

  return (
    <Modal
      title={`Report: ${new Date(report.period_start).toLocaleDateString()} – ${new Date(
        report.period_end
      ).toLocaleDateString()}`}
      onClose={onClose}
    >
      {report.status === "failed" && (
        <Alert variant="error">{report.error_message ?? "Report generation failed."}</Alert>
      )}
      {summary ? (
        <StructuredAnswer answer={summary} />
      ) : (
        report.status === "completed" && (
          <p className="text-sm text-slate-500">Report summary could not be parsed.</p>
        )
      )}
    </Modal>
  );
}
