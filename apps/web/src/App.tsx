import { useEffect, useState } from "react";
import { getToken, listDocuments, login, setToken } from "./api/client";
import { DocumentList } from "./components/DocumentList";
import { UploadForm } from "./components/UploadForm";
import type { DocumentSummary } from "./types";

export default function App() {
  const [loggedIn, setLoggedIn] = useState(() => Boolean(getToken()));
  const [email, setEmail] = useState("alice@example.com");
  const [password, setPassword] = useState("alice-password");
  const [loginError, setLoginError] = useState<string | null>(null);
  const [documents, setDocuments] = useState<DocumentSummary[]>([]);

  async function refreshDocuments() {
    setDocuments(await listDocuments());
  }

  useEffect(() => {
    if (loggedIn) {
      refreshDocuments().catch((err) => console.error(err));
    }
  }, [loggedIn]);

  async function handleLogin(event: React.FormEvent) {
    event.preventDefault();
    setLoginError(null);
    try {
      await login(email, password);
      setLoggedIn(true);
    } catch (err) {
      setLoginError((err as Error).message);
    }
  }

  function handleLogout() {
    setToken(null);
    setLoggedIn(false);
    setDocuments([]);
  }

  if (!loggedIn) {
    return (
      <main style={{ maxWidth: 400, margin: "4rem auto", fontFamily: "sans-serif" }}>
        <h1>Speechify Practice</h1>
        <form onSubmit={handleLogin}>
          <div>
            <input value={email} onChange={(e) => setEmail(e.target.value)} placeholder="Email" />
          </div>
          <div>
            <input
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="Password"
              type="password"
            />
          </div>
          <button type="submit">Log in</button>
        </form>
        {loginError && <p style={{ color: "red" }}>{loginError}</p>}
        <p>
          Seeded users: <code>alice@example.com / alice-password</code>,{" "}
          <code>bob@example.com / bob-password</code>
        </p>
      </main>
    );
  }

  return (
    <main style={{ maxWidth: 600, margin: "2rem auto", fontFamily: "sans-serif" }}>
      <h1>Speechify Practice</h1>
      <button onClick={handleLogout}>Log out</button>
      <UploadForm onCreated={refreshDocuments} />
      <DocumentList documents={documents} onChanged={refreshDocuments} />
    </main>
  );
}
