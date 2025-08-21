// web/src/components/FileList.tsx
import { useEffect, useState } from "react";
import { api } from "../lib/api";
import { FileText, Image as ImageIcon, FileSpreadsheet, Trash2, FileType } from "lucide-react";

type Doc = { id: number; filename: string; size: number };

function iconFor(name: string) {
  const ext = (name.split(".").pop() || "").toLowerCase();
  if (["png", "jpg", "jpeg", "webp", "bmp", "tif", "tiff", "gif"].includes(ext)) return <ImageIcon size={16} />;
  if (["csv", "xlsx", "xls"].includes(ext)) return <FileSpreadsheet size={16} />;
  if (["pdf"].includes(ext)) return <FileType size={16} />;
  return <FileText size={16} />;
}

export default function FileList({ reloadSignal = 0 }: { reloadSignal?: number }) {
  const [docs, setDocs] = useState<Doc[]>([]);
  const [busyId, setBusyId] = useState<number | null>(null);

  async function load() {
    try {
      const d = await api("/api/documents");
      setDocs(d);
    } catch (e) {
      // noop
    }
  }

  useEffect(() => { load(); }, []);
  useEffect(() => { load(); }, [reloadSignal]);

  async function removeDoc(id: number) {
    if (!confirm("Delete this document and its indexed chunks?")) return;
    setBusyId(id);
    try {
      await api(`/api/documents/${id}`, { method: "DELETE" });
      setDocs((prev) => prev.filter((d) => d.id !== id));
    } catch (e: any) {
      alert(e.message || "Delete failed");
    } finally {
      setBusyId(null);
    }
  }

  return (
    <div className="card p-4">
      <div className="flex items-center justify-between mb-2">
        <h3 className="font-semibold">Your documents</h3>
        <button className="btn" onClick={load}>Refresh</button>
      </div>

      <ul className="divide-y">
        {docs.length === 0 && (
          <div className="text-sm text-gray-500">No files yet. Upload to get started.</div>
        )}
        {docs.map((d) => (
          <li key={d.id} className="py-2 flex items-center justify-between">
            <div className="flex items-center gap-2">
              {iconFor(d.filename)}
              <span className="mr-3">{d.filename}</span>
              <span className="text-xs text-gray-500">{(d.size / 1024).toFixed(1)} KB</span>
            </div>
            <button
              className="btn btn-danger"
              onClick={() => removeDoc(d.id)}
              disabled={busyId === d.id}
              title="Remove document"
            >
              {busyId === d.id ? "Deleting..." : (
                <>
                  <Trash2 size={14} />
                  <span className="ml-1">Delete</span>
                </>
              )}
            </button>
          </li>
        ))}
      </ul>
    </div>
  );
}
