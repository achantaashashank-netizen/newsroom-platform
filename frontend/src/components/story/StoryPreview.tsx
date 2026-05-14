"use client";
import { motion, AnimatePresence } from "framer-motion";
import { useStoryStore } from "@/stores/storyStore";
import { useUIStore } from "@/stores/uiStore";
import { cn } from "@/lib/utils";

function Skeleton({ className }: { className?: string }) {
  return (
    <motion.div
      className={cn("bg-white/[0.06] rounded-md", className)}
      animate={{ opacity: [0.4, 0.7, 0.4] }}
      transition={{ duration: 1.6, repeat: Infinity, ease: "easeInOut" }}
    />
  );
}

export function StoryPreview() {
  const story = useStoryStore((s) => s.story);
  const isDirty = useStoryStore((s) => s.isDirty);
  const editField = useStoryStore((s) => s.editField);
  const activeTab = useUIStore((s) => s.activePreviewTab);
  const setActiveTab = useUIStore((s) => s.setActivePreviewTab);

  if (!story) {
    return (
      <div className="h-full flex flex-col items-center justify-center gap-4 text-white/20 p-8">
        <div className="text-5xl">📰</div>
        <div className="text-center space-y-1">
          <p className="text-sm font-medium text-white/30">No story in progress</p>
          <p className="text-xs text-white/20">Enter a topic and run the pipeline to see content generated here in real time</p>
        </div>
      </div>
    );
  }

  const caption = activeTab === "facebook" ? story.caption_facebook : story.caption_instagram;

  return (
    <div className="flex flex-col h-full overflow-y-auto">
      <div className="p-5 space-y-5 flex-1">
        {/* Headline */}
        <div className="space-y-2">
          {story.headline ? (
            <div className="group relative">
              <h1
                contentEditable
                suppressContentEditableWarning
                className="text-xl font-bold text-white/95 leading-snug outline-none border border-transparent focus:border-indigo-500/40 focus:bg-indigo-500/5 rounded-lg px-2 py-1 -mx-2 -my-1 transition-colors"
                onBlur={(e) => editField("headline", e.currentTarget.textContent || "")}
              >
                {story.headline}
              </h1>
              {isDirty && (
                <span className="text-[10px] text-indigo-400 mt-1 inline-block">Edited</span>
              )}
            </div>
          ) : (
            <Skeleton className="h-7 w-4/5" />
          )}
          {story.sub_headline ? (
            <p className="text-sm text-white/55 leading-relaxed">{story.sub_headline}</p>
          ) : (
            <Skeleton className="h-4 w-3/5" />
          )}
        </div>

        {/* Selected image */}
        {story.selected_image_url && (
          <motion.div
            initial={{ opacity: 0, scale: 0.98 }}
            animate={{ opacity: 1, scale: 1 }}
            className="aspect-video rounded-xl overflow-hidden bg-white/[0.04] relative"
          >
            <img
              src={story.selected_image_url}
              alt={story.headline || ""}
              className="w-full h-full object-cover"
            />
          </motion.div>
        )}

        {/* Summary */}
        <div className="space-y-2">
          {story.summary ? (
            <div className="prose prose-sm prose-invert max-w-none">
              <p className="text-sm text-white/70 leading-relaxed whitespace-pre-wrap">{story.summary}</p>
            </div>
          ) : (
            <div className="space-y-2">
              <Skeleton className="h-3.5 w-full" />
              <Skeleton className="h-3.5 w-full" />
              <Skeleton className="h-3.5 w-4/5" />
            </div>
          )}
        </div>

        {/* Bullet points */}
        {story.bullet_points && story.bullet_points.length > 0 && (
          <ul className="space-y-1.5">
            {story.bullet_points.map((point, i) => (
              <motion.li
                key={i}
                initial={{ opacity: 0, x: -6 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: i * 0.05 }}
                className="flex items-start gap-2 text-sm text-white/65"
              >
                <span className="mt-1.5 h-1 w-1 rounded-full bg-indigo-500 shrink-0" />
                {point}
              </motion.li>
            ))}
          </ul>
        )}

        {/* Hashtags */}
        {story.hashtags && story.hashtags.length > 0 && (
          <div className="flex flex-wrap gap-1.5">
            {story.hashtags.map((tag, i) => (
              <span
                key={i}
                className="text-[11px] text-indigo-400 bg-indigo-500/10 border border-indigo-500/20 px-2 py-0.5 rounded-full"
              >
                #{tag}
              </span>
            ))}
          </div>
        )}

        {/* Caption tabs + social card preview */}
        {(story.caption_facebook || story.caption_instagram) && (
          <div className="space-y-3">
            <div className="flex border-b border-white/[0.06]">
              {(["facebook", "instagram"] as const).map((tab) => (
                <button
                  key={tab}
                  onClick={() => setActiveTab(tab)}
                  className={cn(
                    "px-4 py-2 text-xs font-medium capitalize transition-colors border-b-2 -mb-px",
                    activeTab === tab
                      ? "border-indigo-500 text-indigo-400"
                      : "border-transparent text-white/40 hover:text-white/60",
                  )}
                >
                  {tab}
                </button>
              ))}
            </div>

            {/* Social card image preview */}
            {story.social_card_paths?.[activeTab] && (
              <motion.div
                key={activeTab + "-card"}
                initial={{ opacity: 0, scale: 0.97 }}
                animate={{ opacity: 1, scale: 1 }}
                className={cn(
                  "overflow-hidden rounded-xl bg-white/[0.04] relative",
                  activeTab === "facebook" ? "aspect-[1.91/1]" : "aspect-square",
                )}
              >
                <img
                  src={story.social_card_paths[activeTab]}
                  alt={`${activeTab} social card`}
                  className="w-full h-full object-cover"
                />
                <span className="absolute top-2 right-2 text-[10px] bg-black/60 text-white/70 px-2 py-0.5 rounded-full">
                  {activeTab === "facebook" ? "1200×630" : "1080×1080"}
                </span>
              </motion.div>
            )}

            <AnimatePresence mode="wait">
              <motion.p
                key={activeTab}
                initial={{ opacity: 0, y: 4 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0 }}
                className="text-sm text-white/65 leading-relaxed whitespace-pre-wrap"
              >
                {caption}
              </motion.p>
            </AnimatePresence>
          </div>
        )}
      </div>
    </div>
  );
}
