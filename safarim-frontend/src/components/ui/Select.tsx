"use client";

import { useState, useRef, useEffect } from "react";
import { ChevronDown, Check } from "lucide-react";
import { clsx } from "clsx";

export interface SelectOption {
  value: string;
  label: string;
  icon?: React.ReactNode;
}

interface SelectProps {
  options: SelectOption[];
  value?: string;
  onChange?: (value: string) => void;
  placeholder?: string;
  label?: string;
  error?: string;
  disabled?: boolean;
  className?: string;
}

export default function Select({
  options,
  value,
  onChange,
  placeholder = "Tanlang",
  label,
  error,
  disabled,
  className,
}: SelectProps) {
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);
  const selected = options.find((o) => o.value === value);

  useEffect(() => {
    function onClickOutside(e: MouseEvent) {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    }
    document.addEventListener("mousedown", onClickOutside);
    return () => document.removeEventListener("mousedown", onClickOutside);
  }, []);

  return (
    <div className={clsx("w-full space-y-1.5", className)} ref={ref}>
      {label && (
        <label className="block text-sm font-medium text-gray-700">{label}</label>
      )}
      <button
        type="button"
        disabled={disabled}
        onClick={() => setOpen((p) => !p)}
        className={clsx(
          "w-full flex items-center justify-between px-3.5 py-3 rounded-xl border bg-white text-sm transition-all duration-200",
          "focus:outline-none",
          error
            ? "border-red-400 focus:ring-2 focus:ring-red-400/30"
            : open
            ? "border-primary-500 ring-2 ring-primary-500/20"
            : "border-gray-200 hover:border-gray-300",
          disabled && "opacity-50 cursor-not-allowed bg-gray-50"
        )}
      >
        <span className={clsx("truncate", !selected && "text-gray-400")}>
          {selected ? (
            <span className="flex items-center gap-2">
              {selected.icon}
              {selected.label}
            </span>
          ) : placeholder}
        </span>
        <ChevronDown
          size={16}
          className={clsx("text-gray-400 transition-transform duration-200 shrink-0", open && "rotate-180")}
        />
      </button>

      {open && (
        <div className="absolute z-50 mt-1 w-full min-w-[180px] bg-white rounded-xl border border-gray-100 shadow-card-lg py-1 animate-scale-in">
          {options.map((opt) => (
            <button
              key={opt.value}
              type="button"
              onClick={() => { onChange?.(opt.value); setOpen(false); }}
              className={clsx(
                "w-full flex items-center gap-2 px-3.5 py-2.5 text-sm hover:bg-gray-50 transition-colors",
                opt.value === value ? "text-primary-600 font-medium" : "text-gray-700"
              )}
            >
              {opt.icon}
              <span className="flex-1 text-left">{opt.label}</span>
              {opt.value === value && <Check size={14} className="text-primary-500 shrink-0" />}
            </button>
          ))}
        </div>
      )}

      {error && <p className="text-xs text-red-500">{error}</p>}
    </div>
  );
}
