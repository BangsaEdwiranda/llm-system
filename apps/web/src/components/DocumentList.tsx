import { useState } from "react";
import { convertDocument, getDocument } from "../api/client";
import type { DocumentDetail, DocumentSummary } from "../types";

export function DocumentList({
  documents,
  onChanged,
}: {
  documents: DocumentSummary[];
  onChanged: () => void;
}) {
  const [lookupId, setLookupId] = useState("");
  const [lookupResult, setLookupResult] = useState<DocumentDetail | null>(null);
  const [lookupError, setLookupError] = useState<string | null>(null);

  async function handleConvert(id: number) {
    await convertDocument(id);
    onChanged();
  }

  async function handleLookup(event: React.FormEvent) {
    event.preventDefault();
    setLookupError(null);
    setLookupResult(null);
    try {
      const doc = await getDocument(Number(lookupId));
      setLookupResult(doc);
    } catch (err) {
      setLookupError((err as Error).message);
    }
  }

  return (
    <div>
      <h2>Your documents</h2>
      <ul>
        {documents.map((doc) => (
          <li key={doc.id}>
            #{doc.id} <strong>{doc.title}</strong> — {doc.status}
            {doc.audio_url && (
              <>
                {" "}
                <a href={doc.audio_url} target="_blank" rel="noreferrer">
                  audio
                </a>
              </>
            )}
            {doc.status === "not_started" && (
              <button onClick={() => handleConvert(doc.id)} style={{ marginLeft: "0.5rem" }}>
                Convert
              </button>
            )}
          </li>
        ))}
      </ul>

      <h3>Look up a document by ID</h3>
      <form onSubmit={handleLookup}>
        <input
          placeholder="Document ID"
          value={lookupId}
          onChange={(e) => setLookupId(e.target.value)}
        />
        <button type="submit">Fetch</button>
      </form>
      {lookupError && <p style={{ color: "red" }}>{lookupError}</p>}
      {lookupResult && (
        <pre>{JSON.stringify(lookupResult, null, 2)}</pre>
      )}
    </div>
  );
}
