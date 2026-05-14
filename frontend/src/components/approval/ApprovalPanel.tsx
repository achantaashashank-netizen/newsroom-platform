"use client";
import { useState, useEffect } from "react";
import { motion } from "framer-motion";
import { CheckCircle, XCircle, RefreshCw, Settings, TrendingUp, Lightbulb } from "lucide-react";
import { useStoryStore } from "@/stores/storyStore";
import { storyApi, socialApi } from "@/lib/api";
import type { SEOData } from "@/types/story";
import { ConfidenceScore } from "@/components/verification/ConfidenceScore";
import { VerificationBadge } from "@/components/verification/VerificationBadge";
import { cn } from "@/lib/utils";

function SEOPanel({ seo }: { seo: SEOData }) {
  const score = seo.score;
  const color = score >= 75 ? "text-emerald-400" : score >= 50 ? "text-amber-400" : "text-red-400";
  const ring = score >= 75 ? "stroke-emerald-400" : score >= 50 ? "stroke-amber-400" : "stroke-red-400";
  const label = score >= 75 ? "Good" : score >= 50 ? "Needs Work" : "Poor";
  const r = 22;
  const circ = 2 * Math.PI * r;
  const dash = (score / 100) * circ;

  return (
    <motion.div
      initial={{ opacity: 0, y: 6 }}
      animate={{ opacity: 1, y: 0 }}
      className="glass-card p-4 space-y-3"
    >
      <div className="flex items-center gap-2 mb-1">
        <TrendingUp size={13} className="text-indigo-400" />
        <span className="text-xs font-semibold text-white/50 uppercase tracking-widest">SEO Score</span>
      </div>

      <div className="flex items-center gap-4">
        {/* Ring */}
        <div className="relative shrink-0">
          <svg width="56" height="56" viewBox="0 0 56 56">
            <circle cx="28" cy="28" r={r} fill="none" stroke="rgba(255,255,255,0.06)" strokeWidth="4" />
            <circle
              cx="28" cy="28" r={r}
              fill="none"
              className={ring}
              strokeWidth="4"
              strokeLinecap="round"
              strokeDasharray={`${dash} ${circ - dash}`}
              strokeDashoffset={circ / 4}
              style={{ transition: "stroke-dasharray 0.6s ease" }}
            />
          </svg>
          <span className={`absolute inset-0 flex items-center justify-center text-sm font-bold ${color}`}>
            {score}
          </span>
        </div>

        <div className="min-w-0">
          <p className={`text-sm font-semibold ${color}`}>{label}</p>
          <p className="text-[11px] text-white/40 mt-0.5">{seo.readability}</p>
          <p className="text-[11px] text-white/50 mt-1 truncate">
            <span className="text-white/30">Focus: </span>{seo.focus_keyword}
          </p>
        </div>
      </div>

      {/* Keywords */}
      {seo.secondary_keywords?.length > 0 && (
        <div className="flex flex-wrap gap-1">
          {seo.secondary_keywords.slice(0, 5).map((kw) => (
            <span key={kw} className="text-[10px] px-2 py-0.5 rounded-full bg-white/[0.06] text-white/40">
              {kw}
            </span>
          ))}
        </div>
      )}

      {/* Tips */}
      {seo.tips?.length > 0 && (
        <div className="space-y-1.5 border-t border-white/[0.06] pt-3">
          <div className="flex items-center gap-1.5 text-[10px] text-white/30 font-medium uppercase tracking-wider">
            <Lightbulb size={10} />
            Tips
          </div>
          {seo.tips.map((tip, i) => (
            <p key={i} className="text-[11px] text-white/50 leading-snug">• {tip}</p>
          ))}
        </div>
      )}
    </motion.div>
  );
}

interface ConnectedAccount {
  id: string;
  platform: string;
  page_id: string;
  page_name: string;
  instagram_account_id: string | null;
}

interface ApprovalPanelProps {
  runId: string | null;
}

export function ApprovalPanel({ runId }: ApprovalPanelProps) {
  const story = useStoryStore((s) => s.story);
  const applyUpdate = useStoryStore((s) => s.applyUpdate);
  const pendingApproval = useStoryStore((s) => s.pendingApproval);
  const [rejecting, setRejecting] = useState(false);
  const [rejectReason, setRejectReason] = useState("");
  const [loading, setLoading] = useState<"approve" | "reject" | null>(null);
  const [accounts, setAccounts] = useState<ConnectedAccount[]>([]);
  const [selectedTargets, setSelectedTargets] = useState<{ page_id: string; platform: string }[]>([]);
  const [publishing, setPublishing] = useState(false);
  const [published, setPublished] = useState(false);

  useEffect(() => {
    socialApi.list().then((r) => setAccounts(r.data)).catch(() => {});
  }, []);

  // Reset publish state when a new run starts
  useEffect(() => {
    setPublished(false);
    setSelectedTargets([]);
  }, [runId]);

  // Only enable approval actions after the graph has paused at the interrupt
  const canApprove = story?.approval_status === "pending" && runId && !!pendingApproval;
  const isApproved = story?.approval_status === "approved";

  async function handleApprove() {
    if (!runId) return;
    setLoading("approve");
    try {
      await storyApi.approve(runId, "");
      applyUpdate({ approval_status: "approved" });
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(null);
    }
  }

  async function handleReject() {
    if (!runId || !rejectReason.trim()) return;
    setLoading("reject");
    try {
      await storyApi.reject(runId, rejectReason);
      setRejecting(false);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(null);
    }
  }

  async function handlePublish() {
    if (!runId || selectedTargets.length === 0) return;
    setPublishing(true);
    try {
      await storyApi.publish(runId, selectedTargets);
      setPublished(true);
    } catch (e) {
      console.error(e);
    } finally {
      setPublishing(false);
    }
  }

  function toggleTarget(page_id: string, platform: string) {
    setSelectedTargets((prev) => {
      const exists = prev.some((t) => t.page_id === page_id && t.platform === platform);
      return exists
        ? prev.filter((t) => !(t.page_id === page_id && t.platform === platform))
        : [...prev, { page_id, platform }];
    });
  }

  function isSelected(page_id: string, platform: string) {
    return selectedTargets.some((t) => t.page_id === page_id && t.platform === platform);
  }

  return (
    <div className="flex flex-col h-full">
      <div className="px-4 py-3 border-b border-white/[0.06]">
        <span className="text-xs font-semibold text-white/50 uppercase tracking-widest">Editorial</span>
      </div>

      <div className="flex-1 overflow-y-auto p-4 space-y-5">
        {/* Confidence Score */}
        {story?.overall_confidence !== undefined && (
          <div className="glass-card p-4 flex flex-col items-center gap-3">
            <ConfidenceScore
              score={story.overall_confidence}
              tier={story.confidence_tier}
              size={80}
            />
            <VerificationBadge
              tier={story.confidence_tier}
              flags={story.fake_news_flags}
            />
          </div>
        )}

        {/* SEO Score */}
        {story?.seo_data?.score !== undefined && (
          <SEOPanel seo={story.seo_data} />
        )}

        {/* Waiting hint */}
        {!isApproved && !pendingApproval && story && (
          <p className="text-xs text-white/30 text-center">Waiting for pipeline to complete...</p>
        )}

        {/* Approval Actions */}
        {!isApproved && (
          <div className="space-y-2">
            <motion.button
              onClick={handleApprove}
              disabled={!canApprove || loading !== null}
              whileHover={{ scale: canApprove ? 1.02 : 1 }}
              whileTap={{ scale: 0.98 }}
              className={cn(
                "w-full flex items-center justify-center gap-2 py-2.5 px-4 rounded-xl text-sm font-semibold transition-all",
                canApprove
                  ? "bg-emerald-500/90 hover:bg-emerald-500 text-white"
                  : "bg-white/[0.06] text-white/30 cursor-not-allowed",
              )}
            >
              {loading === "approve" ? (
                <RefreshCw size={14} className="animate-spin" />
              ) : (
                <CheckCircle size={14} />
              )}
              Approve Story
            </motion.button>

            {!rejecting ? (
              <button
                onClick={() => setRejecting(true)}
                disabled={!canApprove}
                className={cn(
                  "w-full flex items-center justify-center gap-2 py-2.5 px-4 rounded-xl text-sm font-medium transition-all",
                  canApprove
                    ? "border border-red-500/30 text-red-400 hover:bg-red-500/10"
                    : "border border-white/[0.06] text-white/20 cursor-not-allowed",
                )}
              >
                <XCircle size={14} />
                Reject
              </button>
            ) : (
              <div className="space-y-2">
                <textarea
                  value={rejectReason}
                  onChange={(e) => setRejectReason(e.target.value)}
                  placeholder="Reason for rejection..."
                  rows={3}
                  className="w-full bg-white/[0.04] border border-white/[0.08] rounded-xl px-3 py-2 text-sm text-white/80 placeholder-white/25 outline-none focus:border-red-500/40 resize-none"
                />
                <div className="flex gap-2">
                  <button
                    onClick={handleReject}
                    disabled={!rejectReason.trim() || loading !== null}
                    className="flex-1 py-2 rounded-xl bg-red-500/80 text-white text-xs font-semibold hover:bg-red-500 transition-colors disabled:opacity-40"
                  >
                    Confirm Reject
                  </button>
                  <button
                    onClick={() => setRejecting(false)}
                    className="flex-1 py-2 rounded-xl border border-white/[0.08] text-white/50 text-xs hover:text-white/70 transition-colors"
                  >
                    Cancel
                  </button>
                </div>
              </div>
            )}
          </div>
        )}

        {/* Approved state + Publish */}
        {isApproved && (
          <motion.div
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            className="space-y-4"
          >
            <div className="flex items-center gap-2 text-emerald-400 text-sm font-medium">
              <CheckCircle size={16} />
              {published ? "Published!" : "Story Approved"}
            </div>

            {!published && (
              <>
                <div className="space-y-2">
                  <p className="text-xs text-white/40 font-medium uppercase tracking-wider">Publish to</p>

                  {accounts.length === 0 ? (
                    <div className="text-xs text-white/30 py-3 text-center space-y-2">
                      <p>No accounts connected</p>
                      <a href="/settings" className="flex items-center justify-center gap-1 text-indigo-400 hover:text-indigo-300">
                        <Settings size={11} />
                        Connect in Settings
                      </a>
                    </div>
                  ) : (
                    accounts.map((account) => (
                      <div key={account.id} className="space-y-1.5">
                        {/* Facebook */}
                        <label className="flex items-center gap-3 cursor-pointer group">
                          <div
                            onClick={() => toggleTarget(account.page_id, "facebook")}
                            className={cn(
                              "w-4 h-4 rounded border transition-colors shrink-0",
                              isSelected(account.page_id, "facebook")
                                ? "bg-indigo-500 border-indigo-500"
                                : "border-white/20 group-hover:border-white/40",
                            )}
                          />
                          <div className="min-w-0">
                            <p className="text-xs text-white/70 truncate">{account.page_name}</p>
                            <p className="text-[10px] text-white/30">Facebook Page</p>
                          </div>
                        </label>
                        {/* Instagram (if linked) */}
                        {account.instagram_account_id && (
                          <label className="flex items-center gap-3 cursor-pointer group ml-2">
                            <div
                              onClick={() => toggleTarget(account.instagram_account_id!, "instagram")}
                              className={cn(
                                "w-4 h-4 rounded border transition-colors shrink-0",
                                isSelected(account.instagram_account_id, "instagram")
                                  ? "bg-pink-500 border-pink-500"
                                  : "border-white/20 group-hover:border-white/40",
                              )}
                            />
                            <div className="min-w-0">
                              <p className="text-xs text-white/70 truncate">{account.page_name}</p>
                              <p className="text-[10px] text-white/30">Instagram</p>
                            </div>
                          </label>
                        )}
                      </div>
                    ))
                  )}
                </div>

                {accounts.length > 0 && (
                  <motion.button
                    onClick={handlePublish}
                    disabled={selectedTargets.length === 0 || publishing}
                    whileHover={{ scale: 1.02 }}
                    whileTap={{ scale: 0.98 }}
                    className={cn(
                      "w-full py-2.5 px-4 rounded-xl text-sm font-semibold transition-all flex items-center justify-center gap-2",
                      selectedTargets.length > 0 && !publishing
                        ? "bg-indigo-500/90 hover:bg-indigo-500 text-white"
                        : "bg-white/[0.06] text-white/30 cursor-not-allowed",
                    )}
                  >
                    {publishing && <RefreshCw size={13} className="animate-spin" />}
                    {publishing ? "Publishing..." : "Publish Now"}
                  </motion.button>
                )}
              </>
            )}
          </motion.div>
        )}
      </div>
    </div>
  );
}
