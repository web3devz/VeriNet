"use client";

import { useState, useRef, useCallback } from "react";

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
/*  Main Page                                                          */
/* ------------------------------------------------------------------ */

export default function Home() {
  const [claim, setClaim] = useState("");
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<VerificationResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [history, setHistory] = useState<VerificationResult[]>([]);
  const [queryCount, setQueryCount] = useState(0);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  const verify = useCallback(async (claimText?: string) => {
    const text = (claimText || claim).trim();
    if (!text || loading) return;

    setLoading(true);
    setError(null);
    setResult(null);

    try {
      const res = await fetch("/api/verify", {
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
          <div className="bg-bg-secondary rounded-2xl border border-border-primary focus-within:border-accent/40 transition-colors shadow-lg shadow-black/20">
            <textarea
              ref={inputRef}
              value={claim}
              onChange={(e) => setClaim(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Enter a factual claim to verify..."
              rows={3}
              className="w-full bg-transparent px-5 pt-4 pb-2 text-sm sm:text-base resize-none focus:outline-none placeholder:text-text-muted/40 text-text-primary leading-relaxed"
              disabled={loading}
            />
            <div className="flex items-center justify-between px-4 pb-3">
              <span className="text-[11px] text-text-muted">
                {loading ? "Verifying..." : "Enter to submit"}
              </span>
              <button
                onClick={() => verify()}
                disabled={loading || !claim.trim()}
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
                    <span>Verify</span>
                  </>
                )}
              </button>
            </div>
          </div>
        </div>

        {/* ---- EXAMPLE CHIPS ---- */}
        <div className="flex flex-wrap gap-2 mb-8">
          <span className="text-[11px] text-text-muted py-1.5 font-medium uppercase tracking-wider">Try</span>
          {EXAMPLES.map((ex) => (
            <button
              key={ex}
              onClick={() => handleExample(ex)}
              disabled={loading}
              className="text-xs px-3 py-1.5 rounded-lg border border-border-primary hover:border-accent/40 hover:bg-accent/5 text-text-muted hover:text-accent-hover transition-all duration-150 disabled:opacity-50"
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
