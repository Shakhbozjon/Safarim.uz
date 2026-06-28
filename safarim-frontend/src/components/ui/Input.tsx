import { clsx } from "clsx";
import { forwardRef } from "react";

type InputProps = Omit<React.InputHTMLAttributes<HTMLInputElement>, "prefix"> & {
  label?: string;
  error?: string;
  hint?: string;
  prefix?: React.ReactNode;
  suffix?: React.ReactNode;
};

const Input = forwardRef<HTMLInputElement, InputProps>(
  ({ label, error, hint, prefix, suffix, className, id, ...props }, ref) => {
    const inputId = id || label?.toLowerCase().replace(/\s+/g, "-");

    return (
      <div className="w-full space-y-1.5">
        {label && (
          <label htmlFor={inputId} className="block text-sm font-medium text-gray-700">
            {label}
          </label>
        )}

        <div
          className={clsx(
            "flex items-center w-full rounded-xl border bg-white transition-all duration-200",
            error
              ? "border-red-400 focus-within:ring-2 focus-within:ring-red-400/30"
              : "border-gray-200 focus-within:border-primary-500 focus-within:ring-2 focus-within:ring-primary-500/20"
          )}
        >
          {prefix && (
            <span className="flex items-center pl-3.5 text-gray-500 text-sm select-none shrink-0">
              {prefix}
            </span>
          )}
          <input
            ref={ref}
            id={inputId}
            className={clsx(
              "flex-1 bg-transparent py-3 text-sm text-gray-900 placeholder:text-gray-400 outline-none",
              prefix ? "pl-2 pr-3.5" : "px-3.5",
              suffix ? "pr-2" : "",
              className
            )}
            {...props}
          />
          {suffix && (
            <span className="flex items-center pr-3.5 text-gray-500 shrink-0">
              {suffix}
            </span>
          )}
        </div>

        {error && <p className="text-xs text-red-500">{error}</p>}
        {!error && hint && <p className="text-xs text-gray-400">{hint}</p>}
      </div>
    );
  }
);

Input.displayName = "Input";
export default Input;
