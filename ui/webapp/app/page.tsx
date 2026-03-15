"use client";

import { useState, useRef, useCallback } from "react";
import React from "react";

/* ------------------------------------------------------------------ */
/*  Types                                                              */
/* ------------------------------------------------------------------ */

interface VerificationResult {
  claim: string;
  verdict: string;
  confidence: number;
  sources: string[];
  reasoning: string;
  citation_quality?: number;
  latency_ms?: number;
}

interface WaaPAgent {
  email: string;
  wallet_address: string;
  session_active: boolean;
  policy: Record<string, any>;
}

interface WaaPStatus {
  authenticated: boolean;
  cli_available: boolean;
  agent: WaaPAgent | null;
  boost_multiplier: number;
}

interface PassportStatus {
  address: string;
  network: string;
  verified: boolean;
  verification_count: number;
  fully_verified: boolean;
  gov_id_verified: boolean;
  phone_verified: boolean;
  biometrics_verified: boolean;
  gov_id_expiry?: number;
  phone_expiry?: number;
  biometrics_expiry?: number;
}

interface WalletState {
  connected: boolean;
  address: string | null;
  chainId: number | null;
}

interface UserVerificationState {
  wallet: WalletState;
  passportStatus: PassportStatus | null;
  loading: boolean;
  error: string | null;
}

/* ------------------------------------------------------------------ */
/*  Constants                                                          */
/* ------------------------------------------------------------------ */

const EXAMPLES = [
  "Bitcoin uses proof of stake",
  "The Earth is flat",
  "Water boils at 100 degrees Celsius at standard atmospheric pressure",
  "Python is a compiled programming language",
  "The Moon landing in 1969 was a hoax",
  "DNA stands for deoxyribonucleic acid",
  "JavaScript and Java are the same programming language",
  "The speed of light is approximately 300,000 kilometers per second",
];

/* ------------------------------------------------------------------ */
/*  Helper Functions                                                  */
/* ------------------------------------------------------------------ */

// Helper function to validate Ethereum address format
function isValidEthereumAddress(address: string): boolean {
  return (
    typeof address === "string" &&
    address.startsWith("0x") &&
    address.length === 42 &&
    /^0x[a-fA-F0-9]{40}$/.test(address)
  );
}

/* ------------------------------------------------------------------ */
/*  Icons (inline SVG)                                                 */
/* ------------------------------------------------------------------ */

function IconCheck({ className = "" }: { className?: string }) {
  return (
    <svg className={className} width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
      <polyline points="20 6 9 17 4 12" />
    </svg>
  );
}

function IconX({ className = "" }: { className?: string }) {
  return (
    <svg className={className} width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
      <line x1="18" y1="6" x2="6" y2="18" />
      <line x1="6" y1="6" x2="18" y2="18" />
    </svg>
  );
}

function IconMinus({ className = "" }: { className?: string }) {
  return (
    <svg className={className} width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
      <line x1="5" y1="12" x2="19" y2="12" />
    </svg>
  );
}

function IconArrow({ className = "" }: { className?: string }) {
  return (
    <svg className={className} width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <line x1="5" y1="12" x2="19" y2="12" />
      <polyline points="12 5 19 12 12 19" />
    </svg>
  );
}

function IconShield({ className = "" }: { className?: string }) {
  return (
    <svg className={className} width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />
      <path d="M9 12l2 2 4-4" />
    </svg>
  );
}

function IconBook({ className = "" }: { className?: string }) {
  return (
    <svg className={className} width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M4 19.5A2.5 2.5 0 016.5 17H20" />
      <path d="M6.5 2H20v20H6.5A2.5 2.5 0 014 19.5v-15A2.5 2.5 0 016.5 2z" />
    </svg>
  );
}

function IconClock({ className = "" }: { className?: string }) {
  return (
    <svg className={className} width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <circle cx="12" cy="12" r="10" />
      <polyline points="12 6 12 12 16 14" />
    </svg>
  );
}

function IconUser({ className = "" }: { className?: string }) {
  return (
    <svg className={className} width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M20 21v-2a4 4 0 00-4-4H8a4 4 0 00-4 4v2" />
      <circle cx="12" cy="7" r="4" />
    </svg>
  );
}

function IconLogin({ className = "" }: { className?: string }) {
  return (
    <svg className={className} width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M15 3h4a2 2 0 012 2v14a2 2 0 01-2 2h-4" />
      <polyline points="10 17 15 12 10 7" />
      <line x1="15" y1="12" x2="3" y2="12" />
    </svg>
  );
}

function IconLogout({ className = "" }: { className?: string }) {
  return (
    <svg className={className} width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M9 21H5a2 2 0 01-2-2V5a2 2 0 012-2h4" />
      <polyline points="16 17 21 12 16 7" />
      <line x1="21" y1="12" x2="9" y2="12" />
    </svg>
  );
}

function IconShieldCheck({ className = "" }: { className?: string }) {
  return (
    <svg className={className} width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />
      <path d="M9 12l2 2 4-4" />
    </svg>
  );
}

function IconWallet({ className = "" }: { className?: string }) {
  return (
    <svg className={className} width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M17 14h.01" />
      <path d="M7 7h12a4 4 0 0 1 4 4v6a4 4 0 0 1-4 4H7a4 4 0 0 1-4-4V7a4 4 0 0 1 4 0z" />
      <path d="M7 7V5a2 2 0 0 1 2-2h6a2 2 0 0 1 2 2v2" />
    </svg>
  );
}

function IconDisconnect({ className = "" }: { className?: string }) {
  return (
    <svg className={className} width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4" />
      <polyline points="16 17 21 12 16 7" />
      <line x1="21" y1="12" x2="9" y2="12" />
    </svg>
  );
}

function IconAlert({ className = "" }: { className?: string }) {
  return (
    <svg className={className} width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z" />
      <line x1="12" y1="9" x2="12" y2="13" />
      <line x1="12" y1="17" x2="12.01" y2="17" />
    </svg>
  );
}

function Spinner() {
  return (
    <svg className="anim-spin" width="16" height="16" viewBox="0 0 24 24" fill="none">
      <circle cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="3" strokeDasharray="32" strokeLinecap="round" />
    </svg>
  );
}

/* ------------------------------------------------------------------ */
/*  Verdict Badge                                                      */
/* ------------------------------------------------------------------ */

function VerdictBadge({ verdict, size = "md" }: { verdict: string; size?: "sm" | "md" | "lg" }) {
  const v = verdict?.trim().toLowerCase();

  const styles = {
    true: {
      bg: "bg-success/10 border-success/25",
      text: "text-success",
      icon: <IconCheck className="text-success" />,
      label: "TRUE",
    },
    false: {
      bg: "bg-error/10 border-error/25",
      text: "text-error",
      icon: <IconX className="text-error" />,
      label: "FALSE",
    },
    uncertain: {
      bg: "bg-warning/10 border-warning/25",
      text: "text-warning",
      icon: <IconMinus className="text-warning" />,
      label: "UNCERTAIN",
    },
  };

  const s = styles[v as keyof typeof styles] || styles.uncertain;
  const sizeClass = size === "lg" ? "px-4 py-2 text-base gap-2" : size === "sm" ? "px-2 py-0.5 text-xs gap-1" : "px-3 py-1 text-sm gap-1.5";

  return (
    <span className={`inline-flex items-center rounded-full border font-semibold tracking-wide ${s.bg} ${s.text} ${sizeClass}`}>
      {s.icon}
      {s.label}
    </span>
  );
}

/* ------------------------------------------------------------------ */
/*  Confidence Bar                                                     */
/* ------------------------------------------------------------------ */

function ConfidenceBar({ confidence }: { confidence: number }) {
  const pct = Math.round(confidence * 100);
  let color = "bg-warning";
  if (pct >= 80) color = "bg-success";
  else if (pct >= 60) color = "bg-accent";
  else if (pct < 40) color = "bg-error";

  return (
    <div className="w-full">
      <div className="flex justify-between items-baseline mb-1.5">
        <span className="text-xs font-medium text-text-secondary">Confidence</span>
        <span className="text-sm font-mono font-semibold text-text-primary">{pct}%</span>
      </div>
      <div className="h-2 bg-bg-tertiary rounded-full overflow-hidden">
        <div className={`h-full rounded-full anim-bar ${color}`} style={{ width: `${pct}%` }} />
      </div>
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  Loading Skeleton                                                   */
/* ------------------------------------------------------------------ */

function LoadingSkeleton() {
  return (
    <div className="bg-bg-secondary rounded-2xl border border-border-primary p-6 anim-fade">
      <div className="flex items-center gap-3 mb-6">
        <div className="w-24 h-8 rounded-full anim-shimmer" />
        <div className="flex-1" />
        <div className="w-32 h-8 rounded-lg anim-shimmer" />
      </div>
      <div className="space-y-3 mb-5">
        <div className="h-4 rounded anim-shimmer w-3/4" />
        <div className="h-4 rounded anim-shimmer w-1/2" />
      </div>
      <div className="space-y-2">
        <div className="h-3 rounded anim-shimmer w-2/3" />
        <div className="h-3 rounded anim-shimmer w-1/2" />
        <div className="h-3 rounded anim-shimmer w-3/5" />
      </div>
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  Result Card                                                        */
/* ------------------------------------------------------------------ */

function ResultCard({ result }: { result: VerificationResult }) {
  return (
    <div className="bg-bg-secondary rounded-2xl border border-border-primary overflow-hidden anim-scale">
      {/* Header */}
      <div className="px-6 pt-6 pb-4 flex items-start justify-between gap-4">
        <div>
          <p className="text-xs font-medium text-text-muted uppercase tracking-wider mb-2">Verdict</p>
          <VerdictBadge verdict={result.verdict} size="lg" />
        </div>
        <div className="w-44 pt-1">
          <ConfidenceBar confidence={result.confidence} />
        </div>
      </div>

      <div className="h-px bg-border-primary" />

      {/* Body */}
      <div className="px-6 py-5 space-y-5">
        {/* Claim */}
        <div>
          <p className="text-xs font-medium text-text-muted uppercase tracking-wider mb-1.5">Claim</p>
          <p className="text-sm text-text-secondary leading-relaxed">&ldquo;{result.claim}&rdquo;</p>
        </div>

        {/* Reasoning */}
        {result.reasoning && (
          <div>
            <p className="text-xs font-medium text-text-muted uppercase tracking-wider mb-1.5">Reasoning</p>
            <p className="text-sm text-text-secondary leading-relaxed">{result.reasoning}</p>
          </div>
        )}

        {/* Sources */}
        {result.sources && result.sources.length > 0 && (
          <div>
            <p className="text-xs font-medium text-text-muted uppercase tracking-wider mb-2">
              Sources ({result.sources.length})
            </p>
            <div className="space-y-1.5">
              {result.sources.map((src, i) => (
                <div key={i} className="flex items-start gap-2.5 text-xs group">
                  <span className="shrink-0 w-5 h-5 rounded bg-bg-tertiary flex items-center justify-center text-text-muted font-mono text-[10px]">
                    {i + 1}
                  </span>
                  <div className="flex items-center gap-1.5 text-accent-hover">
                    <IconBook />
                    <span className="break-all">{src}</span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* Footer stats */}
      <div className="px-6 py-3 bg-bg-tertiary/50 border-t border-border-primary flex items-center gap-5 text-xs text-text-muted">
        {result.citation_quality !== undefined && (
          <span className="flex items-center gap-1.5">
            <IconShield className="w-3.5 h-3.5" />
            Citation Quality: <span className="font-mono font-medium text-text-secondary">{Math.round(result.citation_quality * 100)}%</span>
          </span>
        )}
        {result.latency_ms !== undefined && (
          <span className="flex items-center gap-1.5">
            <IconClock />
            Latency: <span className="font-mono font-medium text-text-secondary">{result.latency_ms < 1000 ? `${result.latency_ms}ms` : `${(result.latency_ms / 1000).toFixed(1)}s`}</span>
          </span>
        )}
      </div>
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  History Item                                                       */
/* ------------------------------------------------------------------ */

function HistoryItem({ result, onClick }: { result: VerificationResult; onClick: () => void }) {
  return (
    <button
      onClick={onClick}
      className="w-full text-left bg-bg-secondary hover:bg-bg-tertiary rounded-xl border border-border-primary hover:border-border-secondary px-4 py-3 transition-all duration-150 group"
    >
      <div className="flex items-center justify-between gap-3">
        <span className="text-xs text-text-secondary truncate flex-1">{result.claim}</span>
        <div className="flex items-center gap-2 shrink-0">
          <VerdictBadge verdict={result.verdict} size="sm" />
          <IconArrow className="text-text-muted opacity-0 group-hover:opacity-100 transition-opacity" />
        </div>
      </div>
    </button>
  );
}

/* ------------------------------------------------------------------ */
/*  WaaP Authentication Panel                                          */
/* ------------------------------------------------------------------ */

function WaaPPanel() {
  const [status, setStatus] = useState<WaaPStatus | null>(null);
  const [showSignup, setShowSignup] = useState(false);
  const [showLogin, setShowLogin] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Form states
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [name, setName] = useState("");

  const fetchStatus = async () => {
    try {
      const res = await fetch("/waap/status");
      if (res.ok) {
        const data = await res.json();
        setStatus(data);
      }
    } catch (e) {
      console.warn("Failed to fetch WaaP status:", e);
    }
  };

  const handleSignup = async () => {
    if (!email.trim() || !password.trim()) return;
    setLoading(true);
    setError(null);

    try {
      const res = await fetch("/waap/signup", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email: email.trim(), password, name: name.trim() }),
      });

      const data = await res.json();
      if (data.success) {
        setShowSignup(false);
        setEmail("");
        setPassword("");
        setName("");
        await fetchStatus();
      } else {
        setError(data.error || "Signup failed");
      }
    } catch (e) {
      setError("Network error during signup");
    } finally {
      setLoading(false);
    }
  };

  const handleLogin = async () => {
    if (!email.trim() || !password.trim()) return;
    setLoading(true);
    setError(null);

    try {
      const res = await fetch("/waap/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email: email.trim(), password }),
      });

      const data = await res.json();
      if (data.success) {
        setShowLogin(false);
        setEmail("");
        setPassword("");
        await fetchStatus();
      } else {
        setError(data.error || "Login failed");
      }
    } catch (e) {
      setError("Network error during login");
    } finally {
      setLoading(false);
    }
  };

  const handleLogout = async () => {
    setLoading(true);
    try {
      await fetch("/waap/logout", { method: "POST" });
      await fetchStatus();
    } catch (e) {
      console.warn("Logout error:", e);
    } finally {
      setLoading(false);
    }
  };

  // Load status on mount
  React.useEffect(() => {
    fetchStatus();
  }, []);

  if (!status) {
    return (
      <div className="bg-bg-secondary rounded-xl border border-border-primary p-4">
        <div className="h-4 rounded anim-shimmer w-3/4" />
      </div>
    );
  }

  return (
    <div className="bg-bg-secondary rounded-xl border border-border-primary p-4">
      <h3 className="text-[11px] font-medium text-text-muted uppercase tracking-wider mb-3">
        Agent Authentication
      </h3>

      {status.authenticated && status.agent ? (
        // Authenticated state
        <div className="space-y-3">
          <div className="flex items-center gap-2 text-xs">
            <IconShieldCheck className="text-success" />
            <span className="text-success font-medium">Authenticated</span>
            <span className="text-text-muted">({status.boost_multiplier}x boost)</span>
          </div>

          <div className="space-y-1.5 text-xs">
            <div className="flex justify-between">
              <span className="text-text-muted">Email</span>
              <span className="text-text-secondary font-mono">{status.agent.email}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-text-muted">Wallet</span>
              <span className="text-text-secondary font-mono text-[10px]">
                {status.agent.wallet_address ?
                  `${status.agent.wallet_address.slice(0, 6)}...${status.agent.wallet_address.slice(-4)}` :
                  'Loading...'
                }
              </span>
            </div>
          </div>

          <button
            onClick={handleLogout}
            disabled={loading}
            className="flex items-center gap-1.5 text-xs text-accent hover:text-accent-hover transition-colors disabled:opacity-50"
          >
            <IconLogout />
            <span>Logout</span>
          </button>
        </div>
      ) : (
        // Not authenticated state
        <div className="space-y-3">
          <div className="flex items-center gap-2 text-xs text-text-muted">
            <IconUser />
            <span>Not authenticated</span>
          </div>

          {!status.cli_available && (
            <div className="text-[10px] text-warning bg-warning/10 rounded px-2 py-1">
              WaaP CLI not available
            </div>
          )}

          {error && (
            <div className="text-[10px] text-error bg-error/10 rounded px-2 py-1">
              {error}
            </div>
          )}

          <div className="space-y-2">
            {showSignup ? (
              <div className="space-y-2">
                <input
                  type="email"
                  placeholder="Email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  className="w-full px-2 py-1 text-xs bg-bg-tertiary border border-border-primary rounded focus:outline-none focus:border-accent/40"
                />
                <input
                  type="password"
                  placeholder="Password (≥8 chars)"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className="w-full px-2 py-1 text-xs bg-bg-tertiary border border-border-primary rounded focus:outline-none focus:border-accent/40"
                />
                <input
                  type="text"
                  placeholder="Name (optional)"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  className="w-full px-2 py-1 text-xs bg-bg-tertiary border border-border-primary rounded focus:outline-none focus:border-accent/40"
                />
                <div className="flex gap-1">
                  <button
                    onClick={handleSignup}
                    disabled={loading || !email.trim() || !password.trim()}
                    className="flex-1 px-2 py-1 bg-accent hover:bg-accent-hover text-white text-xs rounded transition-colors disabled:opacity-50"
                  >
                    {loading ? "..." : "Sign Up"}
                  </button>
                  <button
                    onClick={() => { setShowSignup(false); setError(null); }}
                    className="px-2 py-1 text-xs text-text-muted hover:text-text-secondary transition-colors"
                  >
                    Cancel
                  </button>
                </div>
              </div>
            ) : showLogin ? (
              <div className="space-y-2">
                <input
                  type="email"
                  placeholder="Email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  className="w-full px-2 py-1 text-xs bg-bg-tertiary border border-border-primary rounded focus:outline-none focus:border-accent/40"
                />
                <input
                  type="password"
                  placeholder="Password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className="w-full px-2 py-1 text-xs bg-bg-tertiary border border-border-primary rounded focus:outline-none focus:border-accent/40"
                />
                <div className="flex gap-1">
                  <button
                    onClick={handleLogin}
                    disabled={loading || !email.trim() || !password.trim()}
                    className="flex-1 px-2 py-1 bg-accent hover:bg-accent-hover text-white text-xs rounded transition-colors disabled:opacity-50"
                  >
                    {loading ? "..." : "Login"}
                  </button>
                  <button
                    onClick={() => { setShowLogin(false); setError(null); }}
                    className="px-2 py-1 text-xs text-text-muted hover:text-text-secondary transition-colors"
                  >
                    Cancel
                  </button>
                </div>
              </div>
            ) : (
              <div className="space-y-1">
                <button
                  onClick={() => setShowSignup(true)}
                  className="w-full flex items-center gap-1.5 px-2 py-1 text-xs text-accent hover:text-accent-hover transition-colors"
                >
                  <IconUser />
                  <span>Create Agent</span>
                </button>
                <button
                  onClick={() => setShowLogin(true)}
                  className="w-full flex items-center gap-1.5 px-2 py-1 text-xs text-accent hover:text-accent-hover transition-colors"
                >
                  <IconLogin />
                  <span>Login Agent</span>
                </button>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  Passport.xyz Verification Panel                                   */
/* ------------------------------------------------------------------ */

function PassportPanel() {
  const [address, setAddress] = useState("");
  const [network, setNetwork] = useState("optimism");
  const [status, setStatus] = useState<PassportStatus | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const checkVerification = async () => {
    if (!address.trim()) return;

    setLoading(true);
    setError(null);

    try {
      const res = await fetch(`/api/passport/status/${encodeURIComponent(address.trim())}?network=${network}`);
      if (res.ok) {
        const data = await res.json();
        setStatus(data);
      } else {
        const errorData = await res.json().catch(() => ({}));
        setError(errorData.error || `HTTP ${res.status}`);
      }
    } catch (e) {
      setError("Network error occurred");
    } finally {
      setLoading(false);
    }
  };

  const clearStatus = () => {
    setStatus(null);
    setAddress("");
    setError(null);
  };

  const formatExpiry = (timestamp?: number) => {
    if (!timestamp) return null;
    return new Date(timestamp * 1000).toLocaleDateString();
  };

  return (
    <div className="bg-bg-secondary rounded-xl border border-border-primary p-4">
      <h3 className="text-[11px] font-medium text-text-muted uppercase tracking-wider mb-3">
        Human Identity Verification
      </h3>

      <div className="space-y-3">
        {/* Address Input */}
        <div className="space-y-2">
          <input
            type="text"
            placeholder="Blockchain address (0x...)"
            value={address}
            onChange={(e) => setAddress(e.target.value)}
            className="w-full px-2 py-1 text-xs bg-bg-tertiary border border-border-primary rounded focus:outline-none focus:border-accent/40 font-mono"
          />

          <div className="flex gap-1">
            <select
              value={network}
              onChange={(e) => setNetwork(e.target.value)}
              className="flex-1 px-2 py-1 text-xs bg-bg-tertiary border border-border-primary rounded focus:outline-none focus:border-accent/40"
            >
              <option value="optimism">Optimism</option>
              <option value="base-sepolia">Base Sepolia</option>
            </select>

            <button
              onClick={checkVerification}
              disabled={loading || !address.trim()}
              className="px-3 py-1 bg-accent hover:bg-accent-hover text-white text-xs rounded transition-colors disabled:opacity-50"
            >
              {loading ? "..." : "Check"}
            </button>
          </div>
        </div>

        {/* Error Display */}
        {error && (
          <div className="text-[10px] text-error bg-error/10 rounded px-2 py-1">
            {error}
          </div>
        )}

        {/* Verification Status */}
        {status && (
          <div className="space-y-3 border-t border-border-primary pt-3">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2 text-xs">
                {status.verified ? (
                  <>
                    <IconShieldCheck className="text-success" />
                    <span className="text-success font-medium">Verified Human</span>
                  </>
                ) : (
                  <>
                    <IconShield className="text-text-muted" />
                    <span className="text-text-muted font-medium">Unverified</span>
                  </>
                )}
              </div>

              <button
                onClick={clearStatus}
                className="text-xs text-text-muted hover:text-text-secondary transition-colors"
              >
                Clear
              </button>
            </div>

            {status.verified && (
              <>
                <div className="text-[10px] text-accent bg-accent/10 rounded px-2 py-1">
                  {status.verification_count}/3 verifications • {status.fully_verified ? "Fully verified" : "Partial verification"}
                </div>

                <div className="space-y-1.5 text-xs">
                  {/* Government ID */}
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-1.5">
                      {status.gov_id_verified ? (
                        <IconShieldCheck className="w-3 h-3 text-success" />
                      ) : (
                        <IconShield className="w-3 h-3 text-text-muted" />
                      )}
                      <span className={status.gov_id_verified ? "text-text-secondary" : "text-text-muted"}>
                        Government ID
                      </span>
                    </div>
                    {status.gov_id_verified && status.gov_id_expiry && (
                      <span className="text-text-muted text-[10px]">
                        Expires: {formatExpiry(status.gov_id_expiry)}
                      </span>
                    )}
                  </div>

                  {/* Phone */}
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-1.5">
                      {status.phone_verified ? (
                        <IconShieldCheck className="w-3 h-3 text-success" />
                      ) : (
                        <IconShield className="w-3 h-3 text-text-muted" />
                      )}
                      <span className={status.phone_verified ? "text-text-secondary" : "text-text-muted"}>
                        Phone Number
                      </span>
                    </div>
                    {status.phone_verified && status.phone_expiry && (
                      <span className="text-text-muted text-[10px]">
                        Expires: {formatExpiry(status.phone_expiry)}
                      </span>
                    )}
                  </div>

                  {/* Biometrics */}
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-1.5">
                      {status.biometrics_verified ? (
                        <IconShieldCheck className="w-3 h-3 text-success" />
                      ) : (
                        <IconShield className="w-3 h-3 text-text-muted" />
                      )}
                      <span className={status.biometrics_verified ? "text-text-secondary" : "text-text-muted"}>
                        Biometrics
                      </span>
                    </div>
                    {status.biometrics_verified && status.biometrics_expiry && (
                      <span className="text-text-muted text-[10px]">
                        Expires: {formatExpiry(status.biometrics_expiry)}
                      </span>
                    )}
                  </div>
                </div>

                <div className="flex justify-between items-center text-[10px] text-text-muted">
                  <span>Network: {status.network}</span>
                  <span className="font-mono">
                    {status.address.slice(0, 6)}...{status.address.slice(-4)}
                  </span>
                </div>
              </>
            )}

            {!status.verified && (
              <div className="text-[10px] text-text-muted leading-relaxed">
                No Passport.xyz verifications found for this address on {network}.
                Visit passport.xyz to complete identity verification.
              </div>
            )}
          </div>
        )}

        {!status && !loading && (
          <div className="text-[10px] text-text-muted leading-relaxed">
            Check human identity verification status using Passport.xyz.
            Supports Government ID, phone, and biometric verification.
          </div>
        )}
      </div>
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  Wallet Authentication & Verification Gate                         */
/* ------------------------------------------------------------------ */

function WalletAuthPanel() {
  const { userState, setUserState } = useGlobalUserVerification();

  // State for MetaMask availability - start with false to match server rendering
  const [isMetaMaskAvailable, setIsMetaMaskAvailable] = useState(false);

  // Check for MetaMask after component mounts to avoid hydration mismatch
  React.useEffect(() => {
    setIsMetaMaskAvailable(typeof window !== 'undefined' && !!(window as any).ethereum);
  }, []);

  const connectWallet = async () => {
    // Double-check MetaMask availability
    const ethereum = typeof window !== 'undefined' ? (window as any).ethereum : null;

    if (!ethereum) {
      setUserState(prev => ({
        ...prev,
        error: "MetaMask not detected. Please install MetaMask to continue."
      }));
      return;
    }

    setUserState(prev => ({ ...prev, loading: true, error: null }));

    try {
      console.log("Requesting MetaMask accounts...");

      // Add timeout to prevent hanging
      const timeout = new Promise((_, reject) =>
        setTimeout(() => reject(new Error("MetaMask request timed out. Please check for popup blockers and try again.")), 15000)
      );

      const accountsPromise = ethereum.request({ method: 'eth_requestAccounts' });

      // Race between the request and timeout
      const accounts = await Promise.race([accountsPromise, timeout]);

      console.log("MetaMask accounts received:", accounts);

      if (!accounts || accounts.length === 0) {
        throw new Error("No accounts found. Please connect at least one account in MetaMask.");
      }

      const chainId = await ethereum.request({ method: 'eth_chainId' });
      console.log("MetaMask chainId:", chainId);

      const address = accounts[0];
      const numericChainId = parseInt(chainId, 16);

      // Validate address format before proceeding
      if (!isValidEthereumAddress(address)) {
        throw new Error(`Invalid address format received from MetaMask: ${address}. Please try reconnecting your wallet.`);
      }

      console.log("Wallet connected:", { address, chainId: numericChainId });

      setUserState(prev => ({
        ...prev,
        wallet: { connected: true, address, chainId: numericChainId },
        loading: false
      }));

      // Check passport verification after wallet connection
      console.log("Checking passport verification...");
      await checkPassportVerification(address, numericChainId);

    } catch (error: any) {
      setUserState(prev => ({
        ...prev,
        wallet: { connected: false, address: null, chainId: null },
        loading: false,
        error: error.message || "Failed to connect wallet"
      }));
    }
  };

  const checkPassportVerification = async (address: string, chainId?: number) => {
    setUserState(prev => ({ ...prev, loading: true, error: null }));

    try {
      // Determine network based on chainId (use passed chainId or fall back to state)
      const activeChainId = chainId || userState.wallet.chainId;

      // Better network mapping for Passport.xyz
      let network = "optimism"; // Default to optimism
      if (activeChainId === 84532) {
        network = "base-sepolia"; // Base Sepolia testnet
      }
      // For all other chains (including Ethereum mainnet, Sepolia, Optimism), use "optimism"

      console.log("Checking passport for:", { address, chainId: activeChainId, network });

      const res = await fetch(`/api/passport/status/${encodeURIComponent(address)}?network=${network}`);

      console.log("Passport API response status:", res.status);

      if (res.ok) {
        const data = await res.json();
        console.log("Passport verification data:", data);

        setUserState(prev => ({
          ...prev,
          passportStatus: data,
          loading: false,
          error: null // Clear any previous errors
        }));
      } else {
        // Get more detailed error information
        let errorMessage = `API returned ${res.status}`;
        try {
          const errorData = await res.json();
          console.error("Passport verification failed:", errorData);
          errorMessage = errorData.error || errorData.message || errorMessage;
        } catch (jsonError) {
          console.error("Failed to parse error response:", jsonError);
          const textError = await res.text().catch(() => "Unknown error");
          console.error("Error response text:", textError);
          errorMessage = textError || errorMessage;
        }

        setUserState(prev => ({
          ...prev,
          loading: false,
          error: `Verification check failed: ${errorMessage}`
        }));
      }
    } catch (error) {
      console.error("Passport verification error:", error);

      setUserState(prev => ({
        ...prev,
        loading: false,
        error: `Network error: ${error instanceof Error ? error.message : "Unknown error"}`
      }));
    }
  };

  const disconnectWallet = () => {
    setUserState({
      wallet: { connected: false, address: null, chainId: null },
      passportStatus: null,
      loading: false,
      error: null,
    });
  };

  const cancelConnection = () => {
    setUserState(prev => ({
      ...prev,
      loading: false,
      error: null
    }));
  };

  const refreshVerification = () => {
    if (userState.wallet.address) {
      checkPassportVerification(userState.wallet.address);
    }
  };

  const getNetworkName = (chainId: number) => {
    switch (chainId) {
      case 1: return "Ethereum Mainnet";
      case 10: return "Optimism";
      case 11155111: return "Ethereum Sepolia";
      case 84532: return "Base Sepolia";
      default: return `Chain ${chainId}`;
    }
  };

  const isVerified = userState.passportStatus?.verified || false;
  const canUseService = userState.wallet.connected && isVerified;

  return (
    <div className="bg-bg-secondary rounded-xl border border-border-primary p-4">
      <h3 className="text-[11px] font-medium text-text-muted uppercase tracking-wider mb-3">
        Authentication Required
      </h3>

      <div className="space-y-3">
        {/* Wallet Connection Status */}
        <div className="space-y-2">
          {!userState.wallet.connected ? (
            <div className="space-y-2">
              <div className="flex items-center gap-2 text-xs text-text-muted">
                <IconWallet />
                <span>Wallet not connected</span>
              </div>

              {!isMetaMaskAvailable && (
                <div className="text-[10px] text-warning bg-warning/10 rounded px-2 py-1 flex items-center gap-1.5">
                  <IconAlert className="w-3 h-3" />
                  MetaMask required
                </div>
              )}

              {userState.loading ? (
                <div className="space-y-2">
                  <button
                    disabled
                    className="w-full flex items-center justify-center gap-2 px-3 py-2 bg-accent/50 text-white text-xs rounded cursor-not-allowed"
                  >
                    <Spinner />
                    <span>Connecting to MetaMask...</span>
                  </button>
                  <button
                    onClick={cancelConnection}
                    className="w-full flex items-center justify-center gap-1.5 px-2 py-1 text-xs text-text-muted hover:text-text-secondary transition-colors"
                  >
                    <IconX className="w-3 h-3" />
                    <span>Cancel</span>
                  </button>
                  <div className="text-[10px] text-text-muted text-center leading-relaxed">
                    Please check MetaMask for connection popup.
                    <br />
                    If no popup appears, check for popup blockers.
                  </div>
                </div>
              ) : (
                <button
                  onClick={connectWallet}
                  disabled={!isMetaMaskAvailable}
                  className="w-full flex items-center justify-center gap-2 px-3 py-2 bg-accent hover:bg-accent-hover text-white text-xs rounded transition-colors disabled:opacity-50"
                >
                  <IconWallet />
                  <span>Connect Wallet</span>
                </button>
              )}
            </div>
          ) : (
            <div className="space-y-2">
              <div className="flex items-center gap-2 text-xs">
                <IconCheck className="text-success" />
                <span className="text-success font-medium">Wallet Connected</span>
              </div>

              <div className="space-y-1.5 text-xs bg-bg-tertiary/50 rounded p-2">
                <div className="flex justify-between">
                  <span className="text-text-muted">Address</span>
                  <span className="text-text-secondary font-mono text-[10px]">
                    {userState.wallet.address?.slice(0, 6)}...{userState.wallet.address?.slice(-4)}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-text-muted">Network</span>
                  <span className="text-text-secondary text-[10px]">
                    {getNetworkName(userState.wallet.chainId || 0)}
                  </span>
                </div>
              </div>

              <button
                onClick={disconnectWallet}
                className="flex items-center gap-1.5 text-xs text-accent hover:text-accent-hover transition-colors"
              >
                <IconDisconnect />
                <span>Disconnect</span>
              </button>
            </div>
          )}
        </div>

        {/* Passport Verification Status */}
        {userState.wallet.connected && (
          <div className="space-y-2 border-t border-border-primary pt-3">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2 text-xs">
                {isVerified ? (
                  <>
                    <IconShieldCheck className="text-success" />
                    <span className="text-success font-medium">Human Verified</span>
                  </>
                ) : (
                  <>
                    <IconShield className="text-text-muted" />
                    <span className="text-text-muted font-medium">Not Verified</span>
                  </>
                )}
              </div>

              <button
                onClick={refreshVerification}
                disabled={userState.loading}
                className="text-xs text-accent hover:text-accent-hover transition-colors disabled:opacity-50"
              >
                {userState.loading ? "..." : "Refresh"}
              </button>
            </div>

            {userState.passportStatus && isVerified && (
              <div className="text-[10px] text-success bg-success/10 rounded px-2 py-1">
                {userState.passportStatus.verification_count}/3 verifications •
                {userState.passportStatus.fully_verified ? " Fully verified" : " Partial verification"}
              </div>
            )}

            {userState.wallet.connected && !isVerified && (
              <div className="text-[10px] text-warning bg-warning/10 rounded px-2 py-1 leading-relaxed">
                Complete identity verification at{" "}
                <a
                  href="https://passport.xyz"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-accent hover:text-accent-hover underline"
                >
                  passport.xyz
                </a>
                {" "}to access VeriNet fact verification.
              </div>
            )}
          </div>
        )}

        {/* Error Display */}
        {userState.error && (
          <div className="text-[10px] text-error bg-error/10 rounded px-2 py-1 flex items-start gap-1.5">
            <IconAlert className="w-3 h-3 mt-0.5 shrink-0" />
            {userState.error}
          </div>
        )}

        {/* Service Access Status */}
        <div className={`text-[10px] rounded px-2 py-1 ${
          canUseService
            ? "text-success bg-success/10"
            : "text-text-muted bg-bg-tertiary/50"
        }`}>
          {canUseService
            ? "✓ Ready to use VeriNet fact verification"
            : "✗ Wallet connection and human verification required"
          }
        </div>
      </div>
    </div>
  );
}

// Create a global state management using React Context
const UserVerificationContext = React.createContext<{
  userState: UserVerificationState;
  setUserState: React.Dispatch<React.SetStateAction<UserVerificationState>>;
  isAuthenticated: boolean;
} | null>(null);

function UserVerificationProvider({ children }: { children: React.ReactNode }) {
  const [userState, setUserState] = useState<UserVerificationState>({
    wallet: { connected: false, address: null, chainId: null },
    passportStatus: null,
    loading: false,
    error: null,
  });

  const isAuthenticated = userState.wallet.connected && userState.passportStatus?.verified;

  return (
    <UserVerificationContext.Provider value={{ userState, setUserState, isAuthenticated }}>
      {children}
    </UserVerificationContext.Provider>
  );
}

function useGlobalUserVerification() {
  const context = React.useContext(UserVerificationContext);
  if (!context) {
    throw new Error('useGlobalUserVerification must be used within UserVerificationProvider');
  }
  return context;
}

/* ------------------------------------------------------------------ */
/*  Main Page                                                          */
/* ------------------------------------------------------------------ */

function MainApp() {
  const [claim, setClaim] = useState("");
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<VerificationResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [history, setHistory] = useState<VerificationResult[]>([]);
  const [queryCount, setQueryCount] = useState(0);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  // User verification state
  const { userState, isAuthenticated } = useGlobalUserVerification();

  const verify = useCallback(async (claimText?: string) => {
    const text = (claimText || claim).trim();
    if (!text || loading) return;

    // Check authentication before allowing verification
    if (!isAuthenticated) {
      setError("Wallet connection and human verification required to use VeriNet.");
      return;
    }

    setLoading(true);
    setError(null);
    setResult(null);

    try {
      const res = await fetch("/verify", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ claim: text }),
      });

      if (!res.ok) {
        const errData = await res.json().catch(() => ({}));
        throw new Error(errData.error || `HTTP ${res.status}`);
      }

      const data: VerificationResult = await res.json();
      setResult(data);
      setHistory((prev) => [data, ...prev.filter((h) => h.claim !== data.claim)].slice(0, 50));
      setQueryCount((c) => c + 1);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Verification failed.");
    } finally {
      setLoading(false);
    }
  }, [claim, loading]);

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      verify();
    }
  };

  const handleExample = (ex: string) => {
    setClaim(ex);
    verify(ex);
  };

  return (
    <div className="min-h-screen flex flex-col bg-bg-primary">
      {/* ---- HEADER ---- */}
      <header className="sticky top-0 z-50 backdrop-blur-xl bg-bg-primary/80 border-b border-border-primary">
        <div className="max-w-5xl mx-auto px-6 h-14 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-lg bg-accent flex items-center justify-center shadow-lg shadow-accent/20">
              <IconShield className="text-white w-[18px] h-[18px]" />
            </div>
            <span className="font-semibold tracking-tight text-text-primary">VeriNet</span>
          </div>

          <div className="flex items-center gap-4">
            {queryCount > 0 && (
              <span className="text-xs text-text-muted font-mono hidden sm:block">
                {queryCount} {queryCount === 1 ? "query" : "queries"}
              </span>
            )}
            <div className="flex items-center gap-2 text-xs text-text-muted">
              <span className="w-1.5 h-1.5 rounded-full bg-success anim-pulse" />
              <span className="hidden sm:inline">Bittensor Subnet</span>
            </div>
          </div>
        </div>
      </header>

      {/* ---- MAIN ---- */}
      <main className="flex-1 max-w-5xl mx-auto w-full px-6 py-8 sm:py-12">
        {/* Hero */}
        <div className="text-center mb-8 sm:mb-10">
          <h1 className="text-2xl sm:text-3xl lg:text-4xl font-bold tracking-tight mb-3 bg-gradient-to-b from-text-primary to-text-secondary bg-clip-text text-transparent">
            Decentralized Fact Verification
          </h1>
          <p className="text-text-muted text-sm sm:text-base max-w-lg mx-auto leading-relaxed">
            Submit any claim. Get evidence-backed verification from the VeriNet subnet.
            <br className="hidden sm:block" />
            No centralized AI. Fully sovereign.
          </p>
        </div>

        {/* ---- INPUT AREA ---- */}
        <div className="relative mb-4">
          <div className={`bg-bg-secondary rounded-2xl border border-border-primary focus-within:border-accent/40 transition-colors shadow-lg shadow-black/20 ${
            !isAuthenticated ? 'opacity-50 pointer-events-none' : ''
          }`}>
            <textarea
              ref={inputRef}
              value={claim}
              onChange={(e) => setClaim(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder={isAuthenticated
                ? "Enter a factual claim to verify..."
                : "Connect wallet and verify identity to use VeriNet..."
              }
              rows={3}
              className="w-full bg-transparent px-5 pt-4 pb-2 text-sm sm:text-base resize-none focus:outline-none placeholder:text-text-muted/40 text-text-primary leading-relaxed"
              disabled={loading || !isAuthenticated}
            />
            <div className="flex items-center justify-between px-4 pb-3">
              <span className="text-[11px] text-text-muted">
                {!isAuthenticated ? "Authentication required" : loading ? "Verifying..." : "Enter to submit"}
              </span>
              <button
                onClick={() => verify()}
                disabled={loading || !claim.trim() || !isAuthenticated}
                className="px-5 py-2 bg-accent hover:bg-accent-hover active:bg-accent-muted text-white text-sm font-medium rounded-xl transition-all duration-150 disabled:opacity-30 disabled:cursor-not-allowed flex items-center gap-2 shadow-md shadow-accent/20 disabled:shadow-none"
              >
                {loading ? (
                  <>
                    <Spinner />
                    <span>Verifying</span>
                  </>
                ) : (
                  <>
                    <IconShield className="w-4 h-4" />
                    <span>{isAuthenticated ? "Verify" : "Locked"}</span>
                  </>
                )}
              </button>
            </div>
          </div>

          {/* Authentication overlay */}
          {!isAuthenticated && (
            <div className="absolute inset-0 bg-bg-primary/80 backdrop-blur-sm rounded-2xl flex items-center justify-center">
              <div className="bg-bg-secondary rounded-xl border border-border-primary p-4 max-w-xs text-center shadow-lg">
                <IconAlert className="w-8 h-8 text-warning mx-auto mb-2" />
                <h3 className="text-sm font-medium text-text-primary mb-1">Authentication Required</h3>
                <p className="text-xs text-text-muted leading-relaxed">
                  Connect your wallet and complete human identity verification to access VeriNet's decentralized fact verification.
                </p>
              </div>
            </div>
          )}
        </div>

        {/* ---- EXAMPLE CHIPS ---- */}
        <div className="flex flex-wrap gap-2 mb-8">
          <span className="text-[11px] text-text-muted py-1.5 font-medium uppercase tracking-wider">Try</span>
          {EXAMPLES.map((ex) => (
            <button
              key={ex}
              onClick={() => handleExample(ex)}
              disabled={loading || !isAuthenticated}
              className={`text-xs px-3 py-1.5 rounded-lg border border-border-primary transition-all duration-150 ${
                isAuthenticated
                  ? "hover:border-accent/40 hover:bg-accent/5 text-text-muted hover:text-accent-hover"
                  : "text-text-muted/50 cursor-not-allowed"
              } disabled:opacity-50`}
            >
              {ex.length > 40 ? ex.slice(0, 37) + "..." : ex}
            </button>
          ))}
        </div>

        {/* ---- CONTENT AREA ---- */}
        <div className="grid grid-cols-1 lg:grid-cols-[1fr_280px] gap-6">
          {/* Left column: results */}
          <div className="space-y-6 min-w-0">
            {/* Error */}
            {error && (
              <div className="bg-error/5 border border-error/20 rounded-xl px-5 py-4 text-sm text-error anim-slide flex items-start gap-3">
                <IconX className="shrink-0 mt-0.5" />
                <div>
                  <p className="font-medium mb-0.5">Verification Failed</p>
                  <p className="text-error-muted text-xs">{error}</p>
                </div>
              </div>
            )}

            {/* Loading */}
            {loading && <LoadingSkeleton />}

            {/* Result */}
            {result && !loading && <ResultCard result={result} />}

            {/* Empty state */}
            {!result && !loading && !error && (
              <div className="text-center py-16 sm:py-20">
                <div className="w-16 h-16 rounded-2xl bg-bg-secondary border border-border-primary flex items-center justify-center mx-auto mb-4">
                  <IconShield className="w-8 h-8 text-text-muted" />
                </div>
                <p className="text-text-muted text-sm">
                  Enter a claim above to start verifying
                </p>
              </div>
            )}
          </div>

          {/* Right column: sidebar */}
          <aside className="space-y-5">
            {/* Stats card */}
            <div className="bg-bg-secondary rounded-xl border border-border-primary p-4">
              <h3 className="text-[11px] font-medium text-text-muted uppercase tracking-wider mb-3">Network Info</h3>
              <div className="space-y-2.5 text-xs">
                <div className="flex justify-between">
                  <span className="text-text-muted">Protocol</span>
                  <span className="text-text-secondary font-mono">Bittensor</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-text-muted">Verification</span>
                  <span className="text-text-secondary font-mono">Sovereign</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-text-muted">Sources</span>
                  <span className="text-text-secondary font-mono">KB + Wikipedia</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-text-muted">Queries</span>
                  <span className="text-text-secondary font-mono">{queryCount}</span>
                </div>
              </div>
            </div>

            {/* How it works */}
            <div className="bg-bg-secondary rounded-xl border border-border-primary p-4">
              <h3 className="text-[11px] font-medium text-text-muted uppercase tracking-wider mb-3">How It Works</h3>
              <div className="space-y-3 text-xs text-text-muted">
                <div className="flex gap-2.5">
                  <span className="shrink-0 w-5 h-5 rounded bg-accent/10 text-accent flex items-center justify-center font-mono font-bold text-[10px]">1</span>
                  <span>Claim submitted to VeriNet subnet</span>
                </div>
                <div className="flex gap-2.5">
                  <span className="shrink-0 w-5 h-5 rounded bg-accent/10 text-accent flex items-center justify-center font-mono font-bold text-[10px]">2</span>
                  <span>Evidence retrieved from sovereign sources</span>
                </div>
                <div className="flex gap-2.5">
                  <span className="shrink-0 w-5 h-5 rounded bg-accent/10 text-accent flex items-center justify-center font-mono font-bold text-[10px]">3</span>
                  <span>NLI analysis determines verdict</span>
                </div>
                <div className="flex gap-2.5">
                  <span className="shrink-0 w-5 h-5 rounded bg-accent/10 text-accent flex items-center justify-center font-mono font-bold text-[10px]">4</span>
                  <span>Consensus scoring across miners</span>
                </div>
              </div>
            </div>

            {/* Authentication & Verification Gate */}
            <WalletAuthPanel />

            {/* History */}
            {history.length > 0 && (
              <div>
                <h3 className="text-[11px] font-medium text-text-muted uppercase tracking-wider mb-2.5 px-1">
                  History ({history.length})
                </h3>
                <div className="space-y-1.5 max-h-80 overflow-y-auto">
                  {history.map((item, i) => (
                    <HistoryItem
                      key={`${item.claim}-${i}`}
                      result={item}
                      onClick={() => {
                        setResult(item);
                        setClaim(item.claim);
                      }}
                    />
                  ))}
                </div>
              </div>
            )}
          </aside>
        </div>
      </main>

      {/* ---- FOOTER ---- */}
      <footer className="border-t border-border-primary mt-auto">
        <div className="max-w-5xl mx-auto px-6 h-12 flex items-center justify-between text-[11px] text-text-muted">
          <div className="flex items-center gap-2">
            <IconShield className="w-3.5 h-3.5" />
            <span>VeriNet v1.0</span>
          </div>
          <span>Sovereign Fact Verification on Bittensor</span>
        </div>
      </footer>
    </div>
  );
}

export default function Home() {
  return (
    <UserVerificationProvider>
      <MainApp />
    </UserVerificationProvider>
  );
}
