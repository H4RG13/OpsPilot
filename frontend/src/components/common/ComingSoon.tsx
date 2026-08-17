import { Card } from "@/components/ui/Card";

export function ComingSoon({ title }: { title: string }) {
  return (
    <Card>
      <h2 className="text-lg font-semibold text-slate-100">{title}</h2>
      <p className="mt-2 text-sm text-slate-400">
        This section isn&apos;t built yet — it's on the roadmap in{" "}
        <code className="rounded bg-slate-800 px-1 py-0.5 text-xs">PLAN.md</code>.
      </p>
    </Card>
  );
}
