"use client";
import { motion } from "framer-motion";
import { cn } from "@/lib/utils";

interface LiveIndicatorProps {
  isLive: boolean;
  className?: string;
}

export function LiveIndicator({ isLive, className }: LiveIndicatorProps) {
  if (!isLive) return null;
  return (
    <div className={cn("flex items-center gap-1.5", className)}>
      <div className="relative flex items-center justify-center">
        <motion.span
          className="absolute h-2.5 w-2.5 rounded-full bg-red-500/40"
          animate={{ scale: [1, 2, 1], opacity: [0.8, 0, 0.8] }}
          transition={{ duration: 1.8, repeat: Infinity, ease: "easeOut" }}
        />
        <span className="h-2 w-2 rounded-full bg-red-500" />
      </div>
      <span className="text-[10px] font-semibold tracking-widest text-red-400 uppercase">Live</span>
    </div>
  );
}
