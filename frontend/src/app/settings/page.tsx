"use client";
import { useEffect, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { motion } from "framer-motion";
import { ArrowLeft, Link2, Unlink, RefreshCw, Facebook, Instagram } from "lucide-react";
import { socialApi } from "@/lib/api";

interface ConnectedAccount {
  id: string;
  platform: string;
  page_id: string;
  page_name: string;
  page_picture_url: string | null;
  instagram_account_id: string | null;
  token_expires_at: string | null;
  connected_at: string | null;
}

export default function SettingsPage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const [accounts, setAccounts] = useState<ConnectedAccount[]>([]);
  const [loading, setLoading] = useState(true);
  const [connecting, setConnecting] = useState(false);
  const [disconnecting, setDisconnecting] = useState<string | null>(null);
  const [banner, setBanner] = useState<{ type: "success" | "error"; msg: string } | null>(null);

  async function loadAccounts() {
    setLoading(true);
    try {
      const res = await socialApi.list();
      setAccounts(res.data);
    } catch {
      setBanner({ type: "error", msg: "Failed to load connected accounts" });
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    if (!localStorage.getItem("access_token")) {
      router.replace("/login");
      return;
    }
    const connected = searchParams.get("connected");
    const error = searchParams.get("error");
    if (connected) setBanner({ type: "success", msg: `Successfully connected ${connected} Facebook Page(s)` });
    if (error) {
      const msg = error.includes("no_pages")
        ? "No Facebook Pages found. In the Facebook dialog, make sure to check the checkbox next to your Page (e.g. 'Newsroomai') before clicking Continue."
        : `Connection failed: ${error.replace(/_/g, " ")}`;
      setBanner({ type: "error", msg });
    }
    loadAccounts();
  }, [router, searchParams]);

  async function handleConnect() {
    setConnecting(true);
    try {
      const res = await socialApi.authUrl();
      window.location.href = res.data.auth_url;
    } catch {
      setBanner({ type: "error", msg: "Failed to get auth URL" });
      setConnecting(false);
    }
  }

  async function handleDisconnect(id: string) {
    setDisconnecting(id);
    try {
      await socialApi.disconnect(id);
      setAccounts((prev) => prev.filter((a) => a.id !== id));
      setBanner({ type: "success", msg: "Account disconnected" });
    } catch {
      setBanner({ type: "error", msg: "Failed to disconnect" });
    } finally {
      setDisconnecting(null);
    }
  }

  const fbAccounts = accounts.filter((a) => a.platform === "facebook");

  return (
    <div className="min-h-screen bg-[#0a0a0f] text-white">
      <div className="border-b border-white/[0.06] px-6 py-3 flex items-center gap-4">
        <button
          onClick={() => router.push("/newsroom")}
          className="flex items-center gap-1.5 text-xs text-white/40 hover:text-white/70 transition-colors"
        >
          <ArrowLeft size={13} />
          Newsroom
        </button>
        <span className="text-sm font-bold text-white/90 tracking-tight">⚡ Settings</span>
      </div>

      <div className="max-w-2xl mx-auto px-6 py-8 space-y-6">
        {banner && (
          <motion.div
            initial={{ opacity: 0, y: -8 }}
            animate={{ opacity: 1, y: 0 }}
            className={`text-sm px-4 py-3 rounded-xl border ${
              banner.type === "success"
                ? "bg-emerald-500/10 border-emerald-500/20 text-emerald-400"
                : "bg-red-500/10 border-red-500/20 text-red-400"
            }`}
          >
            {banner.msg}
          </motion.div>
        )}

        {/* Meta Accounts */}
        <div className="glass-card p-6 space-y-5">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-sm font-semibold text-white/90">Meta Accounts</h2>
              <p className="text-xs text-white/35 mt-0.5">Connect Facebook Pages and Instagram accounts for publishing</p>
            </div>
            <motion.button
              onClick={handleConnect}
              disabled={connecting}
              whileHover={{ scale: 1.02 }}
              whileTap={{ scale: 0.97 }}
              className="flex items-center gap-2 bg-blue-600/90 hover:bg-blue-600 disabled:opacity-50 text-white text-xs font-semibold px-4 py-2 rounded-xl transition-all"
            >
              {connecting ? <RefreshCw size={13} className="animate-spin" /> : <Link2 size={13} />}
              {connecting ? "Redirecting..." : "Connect Facebook"}
            </motion.button>
          </div>

          {loading ? (
            <div className="space-y-3">
              {[1, 2].map((i) => (
                <motion.div
                  key={i}
                  className="h-16 bg-white/[0.04] rounded-xl"
                  animate={{ opacity: [0.4, 0.7, 0.4] }}
                  transition={{ duration: 1.4, repeat: Infinity, delay: i * 0.1 }}
                />
              ))}
            </div>
          ) : fbAccounts.length === 0 ? (
            <div className="text-center py-8 text-white/25">
              <Facebook size={28} className="mx-auto mb-2 opacity-30" />
              <p className="text-sm">No accounts connected yet</p>
              <p className="text-xs mt-1">Click "Connect Facebook" to link your Pages</p>
            </div>
          ) : (
            <div className="space-y-3">
              {fbAccounts.map((account) => (
                <motion.div
                  key={account.id}
                  initial={{ opacity: 0, y: 6 }}
                  animate={{ opacity: 1, y: 0 }}
                  className="flex items-center gap-4 bg-white/[0.04] border border-white/[0.06] rounded-xl p-4"
                >
                  {account.page_picture_url ? (
                    <img src={account.page_picture_url} alt="" className="w-10 h-10 rounded-full object-cover" />
                  ) : (
                    <div className="w-10 h-10 rounded-full bg-blue-600/30 flex items-center justify-center">
                      <Facebook size={18} className="text-blue-400" />
                    </div>
                  )}

                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium text-white/90 truncate">{account.page_name}</p>
                    <div className="flex items-center gap-3 mt-0.5">
                      <span className="text-[10px] text-white/35">Facebook Page · {account.page_id}</span>
                      {account.instagram_account_id && (
                        <span className="flex items-center gap-1 text-[10px] text-pink-400/70">
                          <Instagram size={10} />
                          Instagram linked
                        </span>
                      )}
                    </div>
                  </div>

                  <button
                    onClick={() => handleDisconnect(account.id)}
                    disabled={disconnecting === account.id}
                    className="flex items-center gap-1.5 text-xs text-white/30 hover:text-red-400 transition-colors disabled:opacity-40"
                  >
                    {disconnecting === account.id ? (
                      <RefreshCw size={12} className="animate-spin" />
                    ) : (
                      <Unlink size={12} />
                    )}
                    Disconnect
                  </button>
                </motion.div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
