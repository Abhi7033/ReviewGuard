import { useState } from "react";
import { analyzeReview, approveThread, type AnalyzeResult } from "./api";

const EXAMPLES = [
  {
    label: "Routine",
    text: "It's fine, I guess. Not great, not terrible.",
  },
  {
    label: "Severe / angry",
    text: "This is the worst purchase I have ever made. It arrived completely broken and I have been trying to get a refund for weeks with no response. Absolutely furious.",
  },
];

const SENTIMENT_STYLES: Record<string, string> = {
  positive: "bg-emerald-100 text-emerald-800 border-emerald-200",
  neutral: "bg-slate-100 text-slate-700 border-slate-200",
  negative: "bg-rose-100 text-rose-800 border-rose-200",
};

function severityColor(severity: number): string {
  if (severity >= 4) return "bg-rose-500";
  if (severity === 3) return "bg-amber-500";
  return "bg-emerald-500";
}

export default function App() {
  const [review, setReview] = useState("");
  const [loading, setLoading] = useState(false);
  const [deciding, setDeciding] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<AnalyzeResult | null>(null);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!review.trim() || loading) return;
    setLoading(true);
    setError(null);
    setResult(null);
    try {
      const res = await analyzeReview(review.trim());
      setResult(res);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Something went wrong.");
    } finally {
      setLoading(false);
    }
  }

  async function handleDecision(approved: boolean) {
    if (!result || deciding) return;
    setDeciding(true);
    setError(null);
    try {
      const res = await approveThread(result.thread_id, approved);
      setResult({ ...res, analysis: result.analysis });
    } catch (err) {
      setError(err instanceof Error ? err.message : "Something went wrong.");
    } finally {
      setDeciding(false);
    }
  }

  const isPending = result?.status === "pending_approval";
  const isDecided = result && ["sent", "not_sent"].includes(result.status);

  return (
    <div className="min-h-screen bg-gradient-to-b from-indigo-50 via-white to-white text-slate-900">
      <div className="mx-auto max-w-2xl px-4 py-10 sm:py-14">
        <header className="mb-8 text-center">
          <h1 className="text-3xl font-bold tracking-tight text-slate-900 sm:text-4xl">
            Review<span className="text-indigo-600">Guard</span>
          </h1>
          <p className="mt-2 text-sm text-slate-500 sm:text-base">
            Paste a customer review — it gets classified, grounded in the knowledge base, and
            escalated for human approval if it's severe enough.
          </p>
        </header>

        <form onSubmit={handleSubmit} className="rounded-2xl bg-white p-4 shadow-sm ring-1 ring-slate-200 sm:p-6">
          <textarea
            value={review}
            onChange={(e) => setReview(e.target.value)}
            placeholder="e.g. My order arrived broken and I want a refund..."
            rows={4}
            className="w-full resize-none rounded-lg border border-slate-200 p-3 text-sm text-slate-800 placeholder:text-slate-400 focus:border-indigo-400 focus:outline-none focus:ring-2 focus:ring-indigo-100 sm:text-base"
          />

          <div className="mt-3 flex flex-wrap gap-2">
            {EXAMPLES.map((ex) => (
              <button
                key={ex.label}
                type="button"
                onClick={() => setReview(ex.text)}
                className="rounded-full border border-slate-200 bg-slate-50 px-3 py-1 text-xs font-medium text-slate-600 transition hover:border-indigo-200 hover:bg-indigo-50 hover:text-indigo-700"
              >
                {ex.label}
              </button>
            ))}
          </div>

          <button
            type="submit"
            disabled={loading || !review.trim()}
            className="mt-4 w-full rounded-lg bg-indigo-600 px-4 py-2.5 text-sm font-semibold text-white transition hover:bg-indigo-700 disabled:cursor-not-allowed disabled:bg-slate-300 sm:text-base"
          >
            {loading ? "Analyzing…" : "Analyze review"}
          </button>
        </form>

        {error && (
          <div className="mt-4 rounded-lg border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700">
            {error}
          </div>
        )}

        {result?.analysis && (
          <div className="mt-6 rounded-2xl bg-white p-5 shadow-sm ring-1 ring-slate-200 sm:p-6">
            <div className="flex flex-wrap items-center gap-2">
              <span
                className={`rounded-full border px-3 py-1 text-xs font-semibold capitalize ${
                  SENTIMENT_STYLES[result.analysis.sentiment] ?? SENTIMENT_STYLES.neutral
                }`}
              >
                {result.analysis.sentiment}
              </span>
              <span className="rounded-full border border-slate-200 bg-slate-50 px-3 py-1 text-xs font-medium text-slate-600">
                {result.analysis.suggested_category}
              </span>
              <div className="ml-auto flex items-center gap-1.5">
                <span className="text-xs font-medium text-slate-500">Severity</span>
                <div className="flex gap-0.5">
                  {[1, 2, 3, 4, 5].map((n) => (
                    <span
                      key={n}
                      className={`h-2 w-4 rounded-sm ${
                        n <= result.analysis!.severity ? severityColor(result.analysis!.severity) : "bg-slate-100"
                      }`}
                    />
                  ))}
                </div>
              </div>
            </div>

            <p className="mt-3 text-sm text-slate-700 sm:text-base">{result.analysis.summary}</p>

            {result.analysis.themes.length > 0 && (
              <div className="mt-3 flex flex-wrap gap-1.5">
                {result.analysis.themes.map((theme) => (
                  <span
                    key={theme}
                    className="rounded-md bg-indigo-50 px-2 py-0.5 text-xs text-indigo-700"
                  >
                    {theme}
                  </span>
                ))}
              </div>
            )}

            {isPending && (
              <div className="mt-5 rounded-xl border border-amber-200 bg-amber-50 p-4">
                <p className="text-sm font-semibold text-amber-800">
                  ⏸ Paused for human approval
                </p>
                <p className="mt-1 text-xs text-amber-700">
                  This review was severe enough to escalate. A support ticket was filed and a
                  resolution was drafted — nothing gets sent to the customer until you decide.
                </p>

                {result.draft_response && (
                  <div className="mt-3 whitespace-pre-wrap rounded-lg bg-white p-3 text-sm text-slate-700 ring-1 ring-amber-100">
                    {result.draft_response.resolution}
                  </div>
                )}

                <div className="mt-3 flex gap-2">
                  <button
                    onClick={() => handleDecision(true)}
                    disabled={deciding}
                    className="flex-1 rounded-lg bg-emerald-600 px-4 py-2 text-sm font-semibold text-white transition hover:bg-emerald-700 disabled:opacity-50"
                  >
                    {deciding ? "…" : "Approve & send"}
                  </button>
                  <button
                    onClick={() => handleDecision(false)}
                    disabled={deciding}
                    className="flex-1 rounded-lg bg-white px-4 py-2 text-sm font-semibold text-slate-700 ring-1 ring-slate-300 transition hover:bg-slate-50 disabled:opacity-50"
                  >
                    {deciding ? "…" : "Reject"}
                  </button>
                </div>
              </div>
            )}

            {!isPending && result.draft_response && (
              <div className="mt-5 rounded-xl border border-slate-200 bg-slate-50 p-4">
                <p className="text-sm font-semibold text-slate-800">
                  {isDecided ? "Sent to customer" : "Draft resolution"}
                </p>
                <div className="mt-2 whitespace-pre-wrap text-sm text-slate-700">
                  {result.draft_response.resolution}
                </div>
                {result.draft_response.sources.length > 0 && (
                  <div className="mt-3 flex flex-wrap gap-1.5">
                    {result.draft_response.sources.map((src) => (
                      <span
                        key={src}
                        className="rounded bg-white px-2 py-0.5 text-xs text-slate-500 ring-1 ring-slate-200"
                      >
                        {src}
                      </span>
                    ))}
                  </div>
                )}
              </div>
            )}

            {result.status === "rejected" && (
              <p className="mt-3 text-xs font-medium text-rose-600">
                Rejected — nothing was sent to the customer.
              </p>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
