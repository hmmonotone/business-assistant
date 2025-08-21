import { useEffect, useState } from "react";

export default function Onboarding({ onDone }: { onDone: () => void }) {
  const [show, setShow] = useState(true);
  useEffect(() => {
    const t = setTimeout(() => { setShow(false); onDone(); }, 1800);
    return () => clearTimeout(t);
  }, []);
  if (!show) return null;
  return (
    <div className="fixed inset-0 z-50 grid place-items-center bg-black/80 text-white">
        <div className="text-center animate-fade-up">
          <h1 className="text-4xl font-semibold">Welcome to your <span className="underline">Business&nbsp;AI</span></h1>
          <p className="mt-3 text-white/80">Ask questions. Upload docs. Get answers with citations.</p>
        </div>
    </div>
  );
}