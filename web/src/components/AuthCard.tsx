import { useState } from "react";
import { api } from "../lib/api";
import { useAuth } from "../store/auth";
import { Eye, EyeOff, Sparkles } from "lucide-react";

export default function AuthCard() {
  const { setUser } = useAuth();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [mode, setMode] = useState<"login" | "register">("register");
  const [error, setError] = useState<string | null>(null);
  const [showPwd, setShowPwd] = useState(false);

  async function submit() {
    setError(null);
    try {
      const res = await api(`/api/auth/${mode}`, {
        method: "POST",
        body: JSON.stringify({ email, password }),
      });
      localStorage.setItem("token", res.token);
      setUser(res.user);
    } catch (e: any) {
      setError(e.message || "Failed");
    }
  }

  return (
    <div className="card p-6 max-w-md w-full">
      <div className="flex items-center gap-2 mb-2 text-gray-600">
        <Sparkles size={16} />
        <span className="text-xs">Welcome to Business AI</span>
      </div>
      <h2 className="text-xl font-semibold mb-4">
        {mode === "register" ? "Create your account" : "Welcome back"}
      </h2>
      <div className="space-y-3">
        <input className="input" placeholder="Email" value={email} onChange={(e) => setEmail(e.target.value)} />
        <div className="relative">
          <input
            className="input pr-10"
            placeholder="Password"
            type={showPwd ? "text" : "password"}
            value={password}
            onChange={(e) => setPassword(e.target.value)}
          />
          <button
            className="absolute right-2 top-1/2 -translate-y-1/2 text-gray-500"
            onClick={() => setShowPwd((s) => !s)}
            aria-label={showPwd ? "Hide password" : "Show password"}
          >
            {showPwd ? <EyeOff size={18} /> : <Eye size={18} />}
          </button>
        </div>
        {error && <div className="text-red-600 text-sm">{error}</div>}
        <button className="btn btn-primary w-full" onClick={submit}>
          {mode === "register" ? "Sign up" : "Sign in"}
        </button>
        <button className="btn w-full" onClick={() => setMode(mode === "register" ? "login" : "register")}>
          {mode === "register" ? "Have an account? Sign in" : "New here? Create account"}
        </button>
      </div>
    </div>
  );
}
