import { forwardRef } from "react";
import type { ButtonHTMLAttributes } from "react";

type Variant = "primary" | "secondary" | "ghost" | "danger";

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: Variant;
  isLoading?: boolean;
}

const VARIANT_CLASSES: Record<Variant, string> = {
  primary: "bg-indigo-500 hover:bg-indigo-400 text-white disabled:bg-indigo-500/50",
  secondary:
    "bg-slate-800 hover:bg-slate-700 text-slate-100 border border-slate-700 disabled:opacity-50",
  ghost: "bg-transparent hover:bg-slate-800 text-slate-300 disabled:opacity-50",
  danger: "bg-red-600 hover:bg-red-500 text-white disabled:bg-red-600/50",
};

export const Button = forwardRef<HTMLButtonElement, ButtonProps>(
  ({ variant = "primary", isLoading, disabled, className = "", children, ...props }, ref) => {
    return (
      <button
        ref={ref}
        disabled={disabled || isLoading}
        className={`inline-flex items-center justify-center gap-2 rounded-md px-4 py-2 text-sm font-medium
          transition-colors disabled:cursor-not-allowed ${VARIANT_CLASSES[variant]} ${className}`}
        {...props}
      >
        {isLoading && (
          <span className="h-3.5 w-3.5 animate-spin rounded-full border-2 border-current border-t-transparent" />
        )}
        {children}
      </button>
    );
  }
);
Button.displayName = "Button";
