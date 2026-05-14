"use client";
import { useState, useCallback } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { TrendingUp, X, RefreshCw, Play, Flame, ChevronRight } from "lucide-react";
import { storyApi } from "@/lib/api";
import { cn } from "@/lib/utils";

interface TrendingTopic {
  keyword: string;
  query: string;
  headline: string;
  summary: string;
  source_count: number;
  sources: string[];
  trending_score: number;
}

interface TrendingPanelProps {
  onGenerate: (query: string) => void;
}

export function TrendingPanel({ onGenerate }: TrendingPanelProps) {
  const [open, setOpen] = useState(false);
  const [topics, setTopics] = useState<TrendingTopic[]>([]);
  const [loading, setLoading] = useState(false);
  const [dismissed, setDismissed] = useState<Set<string>>(new Set());

  const fetchTrending = useCallback(async () => {
    setLoading(true);
    try {
      const res = await storyApi.trending();
      setTopics(res.data);
      setDismissed(new Set());
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  }, []);

  function handleOpen() {
    setOpen(true);
    if (topics.length === 0) fetchTrending();
  }

  function handleGenerate(topic: TrendingTopic) {
    onGenerate(topic.headline);
    setOpen(false);
  }

  function dismiss(keyword: string) {
    setDismissed((prev) => new Set([...prev, keyword]));
  }

  const visible = topics.filter((t) => !dismissed.has(t.keyword));

  return (
    <>
      {/* Trigger button */}
      <button
        onClick={handleOpen}
        className="flex items-center gap-1.5 text-xs text-orange-400/80 hover:text-orange-400 border border-orange-500/20 hover:border-orange-500/40 px-3 py-1.5 rounded-lg transition-all"
      >
        <Flame size={11} />
        Trending
      </button>

      {/* Backdrop */}
      <AnimatePresence>
        {open && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 bg-black/60 backdrop-blur-sm z-40"
            onClick={() => setOpen(false)}
          />
        )}
      </AnimatePresence>

      {/* Drawer */}
      <AnimatePresence>
        {open && (
          <motion.div
            initial={{ x: "100%" }}
            animate={{ x: 0 }}
            exit={{ x: "100%" }}
            transition={{ type: "spring", damping: 28, stiffness: 260 }}
            className="fixed right-0 top-0 h-full w-[480px] bg-[#0d0d14] border-l border-white/[0.08] z-50 flex flex-col"
          >
            {/* Header */}
            <div className="flex items-center justify-between px-5 py-4 border-b border-white/[0.06] shrink-0">
              <div className="flex items-center gap-2">
                <TrendingUp size={15} className="text-orange-400" />
                <span className="text-sm font-semibold text-white/90">Trending Topics</span>
                {!loading && visible.length > 0 && (
                  <span className="text-[10px] text-white/30 bg-white/[0.06] px-2 py-0.5 rounded-full">
                    {visible.length} topics
                  </span>
                )}
              </div>
              <div className="flex items-center gap-2">
                <button
                  onClick={fetchTrending}
                  disabled={loading}
                  className="p-1.5 rounded-lg text-white/30 hover:text-white/60 hover:bg-white/[0.06] transition-all disabled:opacity-40"
                >
                  <RefreshCw size={13} className={loading ? "animate-spin" : ""} />
                </button>
                <button
                  onClick={() => setOpen(false)}
                  className="p-1.5 rounded-lg text-white/30 hover:text-white/60 hover:bg-white/[0.06] transition-all"
                >
                  <X size={14} />
                </button>
              </div>
            </div>

            <p className="px-5 py-2 text-[11px] text-white/25 shrink-0">
              Live from {topics.length > 0 ? "15 RSS feeds" : "..."} · Click Generate to run the full AI pipeline
            </p>

            {/* Topic list */}
            <div className="flex-1 overflow-y-auto px-4 py-2 space-y-2">
              {loading && topics.length === 0 && (
                <div className="space-y-2 pt-2">
                  {Array.from({ length: 8 }).map((_, i) => (
                    <motion.div
                      key={i}
                      className="h-20 bg-white/[0.04] rounded-xl"
                      animate={{ opacity: [0.3, 0.6, 0.3] }}
                      transition={{ duration: 1.4, repeat: Infinity, delay: i * 0.08 }}
                    />
                  ))}
                </div>
              )}

              {!loading && visible.length === 0 && topics.length > 0 && (
                <div className="text-center py-12 text-white/25 text-sm">
                  All topics dismissed.{" "}
                  <button onClick={fetchTrending} className="text-orange-400 hover:text-orange-300">
                    Refresh
                  </button>
                </div>
              )}

              <AnimatePresence initial={false}>
                {visible.map((topic, idx) => (
                  <motion.div
                    key={topic.keyword}
                    initial={{ opacity: 0, y: 8 }}
                    animate={{ opacity: 1, y: 0 }}
                    exit={{ opacity: 0, x: 40, height: 0, marginBottom: 0 }}
                    transition={{ duration: 0.2, delay: idx * 0.03 }}
                    className="group relative bg-white/[0.04] hover:bg-white/[0.06] border border-white/[0.06] hover:border-white/[0.1] rounded-xl p-4 transition-all"
                  >
                    {/* Rank + trending score */}
                    <div className="flex items-start justify-between gap-3 mb-2">
                      <div className="flex items-center gap-2 min-w-0">
                        <span className="text-[10px] font-mono text-white/20 shrink-0 w-5 text-right">
                          {idx + 1}
                        </span>
                        <p className="text-xs font-semibold text-white/85 leading-snug line-clamp-2">
                          {topic.headline}
                        </p>
                      </div>
                      <div className="flex items-center gap-1 shrink-0">
                        <Flame size={10} className={cn(
                          topic.source_count >= 4 ? "text-orange-400" :
                          topic.source_count >= 3 ? "text-amber-400" : "text-white/30"
                        )} />
                        <span className={cn(
                          "text-[10px] font-semibold",
                          topic.source_count >= 4 ? "text-orange-400" :
                          topic.source_count >= 3 ? "text-amber-400" : "text-white/40"
                        )}>
                          {topic.source_count} sources
                        </span>
                      </div>
                    </div>

                    {topic.summary && (
                      <p className="text-[11px] text-white/35 ml-7 mb-2 line-clamp-2 leading-relaxed">
                        {topic.summary.replace(/<[^>]*>/g, "")}
                      </p>
                    )}

                    {/* Sources */}
                    <div className="flex items-center gap-1.5 ml-7 mb-3 flex-wrap">
                      {topic.sources.slice(0, 4).map((s) => (
                        <span key={s} className="text-[9px] text-white/25 bg-white/[0.05] px-1.5 py-0.5 rounded">
                          {s}
                        </span>
                      ))}
                    </div>

                    {/* Actions */}
                    <div className="flex items-center gap-2 ml-7">
                      <motion.button
                        onClick={() => handleGenerate(topic)}
                        whileTap={{ scale: 0.97 }}
                        className="flex items-center gap-1.5 bg-indigo-500/80 hover:bg-indigo-500 text-white text-[11px] font-semibold px-3 py-1.5 rounded-lg transition-all"
                      >
                        <Play size={9} />
                        Generate Article
                      </motion.button>
                      <button
                        onClick={() => dismiss(topic.keyword)}
                        className="text-[11px] text-white/25 hover:text-white/50 px-2 py-1.5 rounded-lg hover:bg-white/[0.06] transition-all"
                      >
                        Dismiss
                      </button>
                    </div>
                  </motion.div>
                ))}
              </AnimatePresence>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </>
  );
}
