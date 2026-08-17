import { Children, isValidElement, useEffect, useLayoutEffect, useMemo, useRef, useState } from "react";
import type { ChangeEvent, KeyboardEvent, ReactNode } from "react";
import { createPortal } from "react-dom";

interface SelectProps {
  label?: string;
  error?: string;
  id?: string;
  name?: string;
  value: string;
  onChange?: (event: ChangeEvent<HTMLSelectElement>) => void;
  disabled?: boolean;
  className?: string;
  children: ReactNode;
}

interface Option {
  value: string;
  label: string;
  disabled: boolean;
}

/** An <option>'s label is often more than one JSX child, e.g.
 * `{product.name} ({formatCurrency(product.price)})` — join whatever text/number
 * nodes are present rather than assuming a single string child. */
function nodeToText(node: ReactNode): string {
  if (node === null || node === undefined || typeof node === "boolean") return "";
  if (typeof node === "string" || typeof node === "number") return String(node);
  if (Array.isArray(node)) return node.map(nodeToText).join("");
  return "";
}

/** Flattens whatever shape of <option> children was passed — including
 * `{items.map(...)}` expressions, which nest an array inside the children
 * list — into a plain list of options. */
function optionsFromChildren(children: ReactNode): Option[] {
  return Children.toArray(children)
    .filter(isValidElement<{ value?: string; disabled?: boolean; children?: ReactNode }>)
    .map((child) => ({
      value: child.props.value ?? "",
      label: nodeToText(child.props.children),
      disabled: Boolean(child.props.disabled),
    }));
}

/** A custom-rendered dropdown (not a native <select>) so the open option list can
 * actually be themed — a native select's popup is OS-rendered and ignores our CSS.
 * Portals the option list to document.body so it always escapes any ancestor
 * `overflow-x-auto` container (e.g. the scrollable tables) instead of being clipped. */
export function Select({
  label,
  error,
  id,
  name,
  value,
  onChange,
  disabled,
  className = "",
  children,
}: SelectProps) {
  const [isOpen, setIsOpen] = useState(false);
  const [highlightedIndex, setHighlightedIndex] = useState(0);
  const [panelStyle, setPanelStyle] = useState<{ top: number; left: number; width: number }>({
    top: 0,
    left: 0,
    width: 0,
  });

  const triggerRef = useRef<HTMLButtonElement>(null);
  const panelRef = useRef<HTMLUListElement>(null);
  const selectId = id ?? name;

  const options = useMemo(() => optionsFromChildren(children), [children]);
  const selectedIndex = options.findIndex((option) => option.value === value);
  const selectedLabel = selectedIndex >= 0 ? options[selectedIndex].label : "";

  useLayoutEffect(() => {
    if (!isOpen || !triggerRef.current) return;
    const rect = triggerRef.current.getBoundingClientRect();
    setPanelStyle({ top: rect.bottom + 4, left: rect.left, width: rect.width });
    setHighlightedIndex(selectedIndex >= 0 ? selectedIndex : 0);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isOpen]);

  useEffect(() => {
    if (!isOpen) return;

    function handlePointerDown(event: MouseEvent) {
      const target = event.target as Node;
      if (triggerRef.current?.contains(target) || panelRef.current?.contains(target)) return;
      setIsOpen(false);
    }
    // Any scroll (including inside a table's own overflow-x-auto container) closes
    // the panel rather than trying to keep a `position: fixed` portal in sync with it.
    function handleScroll() {
      setIsOpen(false);
    }

    document.addEventListener("mousedown", handlePointerDown);
    window.addEventListener("scroll", handleScroll, true);
    return () => {
      document.removeEventListener("mousedown", handlePointerDown);
      window.removeEventListener("scroll", handleScroll, true);
    };
  }, [isOpen]);

  function selectOption(option: Option) {
    if (option.disabled) return;
    setIsOpen(false);
    triggerRef.current?.focus();
    if (option.value === value) return;
    onChange?.({ target: { value: option.value, name } } as ChangeEvent<HTMLSelectElement>);
  }

  function handleTriggerKeyDown(event: KeyboardEvent<HTMLButtonElement>) {
    if (disabled) return;
    if (!isOpen) {
      if (["ArrowDown", "ArrowUp", "Enter", " "].includes(event.key)) {
        event.preventDefault();
        setIsOpen(true);
      }
      return;
    }
    if (event.key === "ArrowDown") {
      event.preventDefault();
      setHighlightedIndex((i) => Math.min(i + 1, options.length - 1));
    } else if (event.key === "ArrowUp") {
      event.preventDefault();
      setHighlightedIndex((i) => Math.max(i - 1, 0));
    } else if (event.key === "Enter" || event.key === " ") {
      event.preventDefault();
      const option = options[highlightedIndex];
      if (option) selectOption(option);
    } else if (event.key === "Escape") {
      event.preventDefault();
      setIsOpen(false);
    } else if (event.key === "Tab") {
      setIsOpen(false);
    }
  }

  return (
    <div className="flex flex-col gap-1.5">
      {label && (
        <label htmlFor={selectId} className="text-sm font-medium text-slate-300">
          {label}
        </label>
      )}
      <button
        ref={triggerRef}
        type="button"
        id={selectId}
        disabled={disabled}
        aria-haspopup="listbox"
        aria-expanded={isOpen}
        onClick={() => setIsOpen((open) => !open)}
        onKeyDown={handleTriggerKeyDown}
        className={`flex items-center justify-between gap-2 rounded-md border bg-slate-900 px-3 py-2 text-left text-sm text-slate-100
          focus:outline-none focus:ring-2 focus:ring-indigo-500/50 disabled:cursor-not-allowed disabled:opacity-50
          ${error ? "border-red-500" : "border-slate-700"} ${className}`}
      >
        <span className="truncate">{selectedLabel}</span>
        <svg
          aria-hidden="true"
          viewBox="0 0 20 20"
          fill="none"
          className={`h-4 w-4 shrink-0 text-slate-500 transition-transform ${isOpen ? "rotate-180" : ""}`}
        >
          <path
            d="M5 7.5L10 12.5L15 7.5"
            stroke="currentColor"
            strokeWidth="1.5"
            strokeLinecap="round"
            strokeLinejoin="round"
          />
        </svg>
      </button>
      {error && <p className="text-xs text-red-400">{error}</p>}

      {isOpen &&
        createPortal(
          <ul
            ref={panelRef}
            role="listbox"
            style={{ position: "fixed", top: panelStyle.top, left: panelStyle.left, width: panelStyle.width }}
            className="z-50 max-h-60 overflow-y-auto rounded-md border border-slate-700 bg-slate-900 py-1 shadow-xl"
          >
            {options.map((option, index) => (
              <li
                key={option.value}
                role="option"
                aria-selected={option.value === value}
                onMouseEnter={() => setHighlightedIndex(index)}
                onClick={() => selectOption(option)}
                className={`cursor-pointer truncate px-3 py-2 text-sm ${
                  option.disabled
                    ? "cursor-not-allowed text-slate-600"
                    : option.value === value
                      ? "bg-indigo-500/15 text-indigo-300"
                      : index === highlightedIndex
                        ? "bg-slate-800 text-slate-100"
                        : "text-slate-300"
                }`}
              >
                {option.label}
              </li>
            ))}
          </ul>,
          document.body
        )}
    </div>
  );
}
