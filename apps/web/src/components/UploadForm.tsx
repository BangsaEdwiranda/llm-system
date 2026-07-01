import { useState } from "react";
import { createDocument } from "../api/client";

export function UploadForm({ onCreated }: { onCreated: () => void }) {
  const [title, setTitle] = useState("");
  const [text, setText] = useState("");
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(event: React.FormEvent) {
    event.preventDefault();
    setError(null);
    try {
      await createDocument(title, text);
      setTitle("");
      setText("");
      onCreated();
    } catch (err) {
      setError((err as Error).message);
    }
  }

  return (
    <form onSubmit={handleSubmit} style={{ marginBottom: "1.5rem" }}>
      <h2>New document</h2>
      <div>
        <input
          placeholder="Title"
          value={title}
          onChange={(e) => setTitle(e.target.value)}
          required
        />
      </div>
      <div>
        <textarea
          placeholder="Document text"
          value={text}
          onChange={(e) => setText(e.target.value)}
          rows={4}
          required
        />
      </div>
      <button type="submit">Create</button>
      {error && <p style={{ color: "red" }}>{error}</p>}
    </form>
  );
}
