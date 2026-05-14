"use client";
import { motion } from "framer-motion";
import { cn, formatConfidence } from "@/lib/utils";

interface ConfidenceScoreProps {
  score: number;
  tier?: "low" | "medium" | "high";
  size?: number;
}

export function ConfidenceScore({ score, tier = "medium", size = 72 }: ConfidenceScoreProps) {
  const radius = (size - 8) / 2;
  const circumference = 2 * Math.PI * radius;
  const dashOffset = circumference * (1 - score);

  const tierColor = {
    high: "#22c55e",
    medium: "#f59e0b",
    low: "#ef4444",
  }[tier];

  return (
    <div className="flex flex-col items-center gap-1">
      <div className="relative" style={{ width: size, height: size }}>
        <svg width={size} height={size} className="-rotate-90">
          <circle
            cx={size / 2}
            cy={size / 2}
            r={radius}
            fill="none"
            stroke="rgba(255,255,255,0.08)"
            strokeWidth={4}
          />
          <motion.circle
            cx={size / 2}
            cy={size / 2}
            r={radius}
            fill="none"
            stroke={tierColor}
            strokeWidth={4}
            strokeLinecap="round"
            strokeDasharray={circumference}
            initial={{ strokeDashoffset: circumference }}
            animate={{ strokeDashoffset: dashOffset }}
            transition={{ duration: 1.2, ease: "easeOut" }}
          />
        </svg>
        <div className="absolute inset-0 flex items-center justify-center">
          <span className="text-sm font-bold" style={{ color: tierColor }}>
            {formatConfidence(score)}
          </span>
        </div>
      </div>
      <span
        className={cn(
          "text-[10px] font-semibold uppercase tracking-widest px-2 py-0.5 rounded-full",
          tier === "high" && "bg-emerald-500/15 text-emerald-400",
          tier === "medium" && "bg-amber-500/15 text-amber-400",
          tier === "low" && "bg-red-500/15 text-red-400",
        )}
      >
        {tier}
      </span>
    </div>
  );
}
