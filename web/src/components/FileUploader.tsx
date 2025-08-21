import { upload } from "../lib/api";
import { useState, useRef } from "react";
import { UploadCloud } from "lucide-react";

export default function FileUploader({ onUploaded }: { onUploaded: () => void }) {
  const [busy, setBusy] = useState(false);
  const [count, setCount] = useState(0);
  const inputRef = useRef<HTMLInputElement>(null);

  async function send(files: FileList) {
    if (!files || files.length === 0) return;
    const fd = new FormData();
    for (let i = 0; i < files.length; i++) fd.append("files", files.item(i)!);
    setBusy(true); setCount(files.length);
    try { await upload("/api/documents/upload/batch", fd); onUploaded(); }
    catch { alert("Upload failed"); }
    finally { setBusy(false); setCount(0); if (inputRef.current) inputRef.current.value = ""; }
  }

  function onChange(e: React.ChangeEvent<HTMLInputElement>) { if (e.target.files) send(e.target.files); }

  return (
    <div
      className="card p-4 border-dashed border-2 hover:border-gray-300 transition"
      onDragOver={(e) => e.preventDefault()}
      onDrop={(e) => { e.preventDefault(); if (e.dataTransfer.files) send(e.dataTransfer.files); }}
    >
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <UploadCloud size={18} />
          <div className="text-sm">
            Drag & drop files here, or{" "}
            <button className="btn btn-primary px-2 py-1" onClick={() => inputRef.current?.click()}>
              {busy ? `Uploading ${count}…` : "Browse"}
            </button>
          </div>
        </div>
        <input
          ref={inputRef}
          type="file"
          className="hidden"
          onChange={onChange}
          multiple
          accept=".pdf,.docx,.txt,.md,.png,.jpg,.jpeg,.webp,.bmp,.tif,.tiff"
        />
      </div>
    </div>
  );
}
