"use client";

import { clsx } from "clsx";

export interface TabItem {
  key: string;
  label: string;
  icon?: React.ReactNode;
  badge?: number;
}

interface TabsProps {
  tabs: TabItem[];
  active: string;
  onChange: (key: string) => void;
  variant?: "line" | "pill";
  className?: string;
}

export default function Tabs({ tabs, active, onChange, variant = "line", className }: TabsProps) {
  if (variant === "pill") {
    return (
      <div className={clsx("flex gap-2 flex-wrap", className)}>
        {tabs.map((tab) => (
          <button
            key={tab.key}
            onClick={() => onChange(tab.key)}
            className={clsx(
              "inline-flex items-center gap-1.5 px-4 py-2 rounded-xl text-sm font-medium transition-all duration-200",
              tab.key === active
                ? "bg-primary-500 text-white shadow-sm"
                : "bg-white text-gray-600 border border-gray-200 hover:border-gray-300 hover:bg-gray-50"
            )}
          >
            {tab.icon}
            {tab.label}
            {tab.badge !== undefined && tab.badge > 0 && (
              <span className={clsx(
                "text-xs px-1.5 py-0.5 rounded-full font-semibold",
                tab.key === active ? "bg-white/20 text-white" : "bg-gray-100 text-gray-600"
              )}>
                {tab.badge}
              </span>
            )}
          </button>
        ))}
      </div>
    );
  }

  return (
    <div className={clsx("border-b border-gray-100", className)}>
      <nav className="-mb-px flex gap-0">
        {tabs.map((tab) => (
          <button
            key={tab.key}
            onClick={() => onChange(tab.key)}
            className={clsx(
              "inline-flex items-center gap-1.5 px-5 py-3.5 text-sm font-medium border-b-2 transition-all duration-200 whitespace-nowrap",
              tab.key === active
                ? "border-primary-500 text-primary-600"
                : "border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-200"
            )}
          >
            {tab.icon}
            {tab.label}
            {tab.badge !== undefined && tab.badge > 0 && (
              <span className={clsx(
                "text-xs px-1.5 py-0.5 rounded-full font-semibold ml-0.5",
                tab.key === active ? "bg-primary-100 text-primary-600" : "bg-gray-100 text-gray-500"
              )}>
                {tab.badge}
              </span>
            )}
          </button>
        ))}
      </nav>
    </div>
  );
}
