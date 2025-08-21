import { useEffect, useState } from "react";
import Onboarding from "./components/Onboarding";
import AuthCard from "./components/AuthCard";
import Dashboard from "./pages/Dashboard";
import Chat from "./pages/Chat";
import { useAuth } from "./store/auth";
import "./styles.css";
import { api } from "./lib/api";

export default function App() {
  const { user, setUser } = useAuth();
  const [seenOnboard, setSeenOnboard] = useState(false);
  const [tab, setTab] = useState<"dashboard" | "chat">("dashboard");

  useEffect(() => {
    const token = localStorage.getItem("token");
    if (!token) return;
    api("/api/auth/profile").then((u) => setUser(u)).catch(() => localStorage.removeItem("token"));
  }, []);

  function handleLogout() {
    localStorage.removeItem("token");
    setUser(null);
    setTab("dashboard");
  }

  async function handleDeleteAccount() {
  const warn = confirm(
    "This will permanently delete your account and all uploaded documents. Continue?"
  );
  if (!warn) return;

  const password = prompt("Please confirm your password to delete your account:");
  if (!password) return;

  try {
    await api("/api/auth/delete-account", {
      method: "POST",
      body: JSON.stringify({ password }),
    });
    localStorage.removeItem("token");
    setUser(null);
    alert("Your account was deleted.");
  } catch (e: any) {
    alert(e.message || "Failed to delete account");
  }
}

  return (
    <div>
      {!seenOnboard && <Onboarding onDone={() => setSeenOnboard(true)} />}

      <header className="header-glass sticky top-0 z-40">
        <div className="max-w-5xl mx-auto px-4 h-14 flex items-center justify-between">
          <div className="brand">🧠 Business AI</div>
          <nav className="flex items-center gap-2">
            <div className="segmented">
              <button className={tab==="dashboard" ? "active" : ""} onClick={() => setTab("dashboard")}>Dashboard</button>
              <button className={tab==="chat" ? "active" : ""} onClick={() => setTab("chat")}>Chat</button>
            </div>
            {user && <div className="ml-2 text-sm text-gray-600">{user.email}</div>}
            {user && (
                <>
                  <button className="btn btn-ghost" onClick={handleLogout}>Logout</button>
                  <button className="btn btn-danger" onClick={handleDeleteAccount}>Delete account</button>
                </>
            )}
          </nav>
        </div>
      </header>

      <main className="max-w-5xl mx-auto px-4 py-6">
        {!user ? (
          <div className="grid place-items-center min-h-[60vh]"><AuthCard /></div>
        ) : tab === "dashboard" ? <Dashboard onUploaded={() => {}} /> : <Chat />}
      </main>
    </div>
  );
}
