"use client";
import { Shield, ShieldAlert, ShieldCheck } from "lucide-react";
import { cn } from "@/lib/utils";

interface VerificationBadgeProps {
  tier?: "low" | "medium" | "high";
  flags?: string[];
}

export function VerificationBadge({ tier = "medium", flags = [] }: VerificationBadgeProps) {
  const config = {
    high: {
      icon: ShieldCheck,
      label: "Verified",
      className: "text-emerald-400 border-emerald-500/20 bg-emerald-500/10",
    },
    medium: {
      icon: Shield,
      label: "Partially Verified",
      className: "text-amber-400 border-amber-500/20 bg-amber-500/10",
    },
    low: {
      icon: ShieldAlert,
      label: "Unverified",
      className: "text-red-400 border-red-500/20 bg-red-500/10",
    },
  }[tier];

  const Icon = config.icon;

  return (
    <div className="space-y-2">
      <div className={cn("inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full border text-xs font-medium", config.className)}>
        <Icon size={12} />
        {config.label}
      </div>
      {flags.length > 0 && (
        <ul className="space-y-1">
          {flags.map((flag, i) => (
            <li key={i} className="flex items-start gap-1.5 text-[11px] text-red-400/80">
              <span className="mt-0.5 shrink-0">⚠</span>
              <span>{flag}</span>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
