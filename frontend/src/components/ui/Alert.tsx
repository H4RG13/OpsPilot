import type { ReactNode } from "react";

interface AlertProps {
  variant?: "error" | "info" | "success";
  children: ReactNode;
}

const VARIANT_CLASSES = {
  error: "border-red-500/40 bg-red-500/10 text-red-300",
  info: "border-indigo-500/40 bg-indigo-500/10 text-indigo-300",
  success: "border-emerald-500/40 bg-emerald-500/10 text-emerald-300",
};

export function Alert({ variant = "info", children }: AlertProps) {
  return (
    <div className={`rounded-md border px-3 py-2 text-sm ${VARIANT_CLASSES[variant]}`} role="alert">
      {children}
    </div>
  );
}
