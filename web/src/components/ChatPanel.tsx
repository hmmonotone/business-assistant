import { useState } from "react";
import { api, apiDownload } from "../lib/api";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { Copy, Send, Loader2, FileDown, Lightbulb } from "lucide-react";

type Source = {
  document_id: number;
  filename: string;
  page?: number | null;
  text: string;
  url?: string; // /api/documents/{id}/download
};
type QA = { q: string; a: string; sources: Source[] };

const SUGGESTED = [
  "Summarize April revenue (bullets)",
  "Top 3 customer complaints with citations",
  "Which days had highest sales in April?",
  "List positive feedback themes with examples"
];

export default function ChatPanel() {
  const [q, setQ] = useState("");
  const [items, setItems] = useState<QA[]>([]);
  const [busy, setBusy] = useState(false);

  async function ask(text?: string) {
    const query = (text ?? q).trim();
    if (!query) return;
    setBusy(true);
    try {
      const history = items.slice(0, 3).reverse().flatMap((it) => [
        { role: "user" as const, content: it.q },
        { role: "assistant" as const, content: it.a },
      ]);
      const prev_context_full = items
        .slice(0, 3)
        .flatMap((it) => (it.sources ?? []).map((s) => s.text))
        .join("\n\n");
      const prev_context = prev_context_full.slice(-4000);

      const res = await api("/api/knowledge/ask", {
        method: "POST",
        body: JSON.stringify({ question: query, top_k: 6, prev_context, history }),
      });

      setItems((prev) => [{ q: query, a: res.answer, sources: res.sources || [] }, ...prev]);
      setQ("");
    } catch (e: any) {
      alert(e.message || "Failed");
    } finally {
      setBusy(false);
    }
  }

  async function downloadSource(s: Source) {
    try {
      const path = s.url || `/api/documents/${s.document_id}/download`;
      const blob = await apiDownload(path);
      const href = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = href; a.download = s.filename || "document";
      document.body.appendChild(a); a.click(); a.remove();
      URL.revokeObjectURL(href);
    } catch (e: any) {
      alert(e.message || "Download failed");
    }
  }

  function copy(text: string) {
    navigator.clipboard.writeText(text);
  }

  return (
    <div className="card p-4 space-y-4">
      {/* composer */}
      <div className="flex gap-2">
        <input
          className="input"
          placeholder="Ask about your docs... (Shift+Enter for newline)"
          value={q}
          onChange={(e) => setQ(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); ask(); }
          }}
          disabled={busy}
        />
        <button className="btn btn-primary" onClick={() => ask()} disabled={busy}>
          {busy ? <Loader2 className="animate-spin" size={18} /> : <Send size={18} />}
        </button>
      </div>

      {/* suggestions */}
      {items.length === 0 && (
        <div className="card p-4">
          <div className="flex items-center gap-2 text-sm text-gray-600 mb-2">
            <Lightbulb size={16} /> Try one:
          </div>
          <div className="flex flex-wrap gap-2">
            {SUGGESTED.map((s) => (
              <button key={s} className="btn-chip" onClick={() => ask(s)}>{s}</button>
            ))}
          </div>
        </div>
      )}

      {/* chats */}
      <div className="space-y-4">
        {items.map((it, idx) => (
          <div key={idx} className="border rounded-xl p-3">
            <div className="text-sm text-gray-600">You: {it.q}</div>

            <div className="mt-2 answer">
              <ReactMarkdown remarkPlugins={[remarkGfm]}>
                {it.a || ""}
              </ReactMarkdown>
            </div>

            {/* actions */}
            <div className="mt-2 flex items-center gap-2">
              <button className="btn btn-ghost text-xs" onClick={() => copy(it.a)}>
                <Copy size={14} /> Copy
              </button>
            </div>

            {/* sources */}
            {it.sources?.length > 0 && (
              <div className="mt-3">
                <div className="text-xs font-medium text-gray-600 mb-1">Sources</div>
                <div className="flex flex-wrap gap-2">
                  {it.sources.map((s, i) => (
                    <button
                      key={i}
                      onClick={() => downloadSource(s)}
                      className="btn-chip"
                      title={`Download ${s.filename}`}
                    >
                      <span className="font-semibold">[{i + 1}]</span>&nbsp;
                      <span>{s.filename}</span>
                      {s.page != null && <span className="text-gray-500">&nbsp;(p.{s.page})</span>}
                      <FileDown size={14} className="ml-1" />
                    </button>
                  ))}
                </div>
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
