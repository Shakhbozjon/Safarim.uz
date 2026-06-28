"use client";

import { useRef } from "react";
import { clsx } from "clsx";

interface OtpInputProps {
  value: string;
  onChange: (value: string) => void;
  error?: string;
  disabled?: boolean;
}

export default function OtpInput({ value, onChange, error, disabled }: OtpInputProps) {
  const inputs = useRef<(HTMLInputElement | null)[]>([]);
  const digits = value.split("").concat(Array(6).fill("")).slice(0, 6);

  function handleChange(index: number, char: string) {
    if (!/^\d*$/.test(char)) return;
    const newDigits = [...digits];
    newDigits[index] = char.slice(-1);
    onChange(newDigits.join("").replace(/\s/g, ""));
    if (char && index < 5) inputs.current[index + 1]?.focus();
  }

  function handleKeyDown(index: number, e: React.KeyboardEvent) {
    if (e.key === "Backspace" && !digits[index] && index > 0) {
      inputs.current[index - 1]?.focus();
    }
    if (e.key === "ArrowLeft" && index > 0) inputs.current[index - 1]?.focus();
    if (e.key === "ArrowRight" && index < 5) inputs.current[index + 1]?.focus();
  }

  function handlePaste(e: React.ClipboardEvent) {
    e.preventDefault();
    const pasted = e.clipboardData.getData("text").replace(/\D/g, "").slice(0, 6);
    onChange(pasted);
    inputs.current[Math.min(pasted.length, 5)]?.focus();
  }

  return (
    <div className="space-y-2">
      <div className="flex gap-2.5 justify-center">
        {digits.map((digit, i) => (
          <input
            key={i}
            ref={(el) => { inputs.current[i] = el; }}
            type="text"
            inputMode="numeric"
            maxLength={1}
            value={digit}
            disabled={disabled}
            onChange={(e) => handleChange(i, e.target.value)}
            onKeyDown={(e) => handleKeyDown(i, e)}
            onPaste={handlePaste}
            className={clsx(
              "w-11 h-13 text-center text-xl font-semibold rounded-xl border-2 outline-none transition-all duration-200",
              "focus:border-primary-500 focus:ring-2 focus:ring-primary-500/20",
              digit ? "bg-primary-50 border-primary-400 text-primary-700" : "bg-white border-gray-200 text-gray-900",
              error ? "border-red-400" : "",
              disabled ? "opacity-50 cursor-not-allowed bg-gray-50" : ""
            )}
          />
        ))}
      </div>
      {error && <p className="text-xs text-red-500 text-center">{error}</p>}
    </div>
  );
}
