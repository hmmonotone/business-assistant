import { useState } from "react";
import FileUploader from "../components/FileUploader";
import FileList from "../components/FileList";

export default function Dashboard({ onUploaded }: { onUploaded: () => void }) {
  const [reload, setReload] = useState(0);

  return (
    <div className="grid gap-6 md:grid-cols-2">
      <div className="space-y-3">
        <div className="card p-6">
          <h2 className="text-xl font-semibold mb-2">Upload documents</h2>
          <p className="text-sm text-gray-600 mb-4">
            PDF, DOCX, TXT, MD, or images. We extract text and index privately for your account.
          </p>
          <FileUploader onUploaded={() => setReload((n) => n + 1)} />
        </div>
        <FileList reloadSignal={reload} />
      </div>
      <div className="hidden md:block self-start">
        <div className="card p-6">
          <h3 className="font-semibold mb-2">Tips</h3>
          <ul className="list-disc ml-5 text-sm text-gray-600 space-y-1">
            <li>Upload a few focused documents for best answers.</li>
            <li>Ask precise questions like “summarize page 3 meeting notes.”</li>
            <li>We cite sources with filename and page.</li>
          </ul>
        </div>
      </div>
    </div>
  );
}
