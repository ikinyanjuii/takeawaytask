"use client";

import { useEffect, useState } from "react";

type Feature = {
  id: number; title: string; description: string; customer_segment: string;
  vote_count: number; theme?: string; underlying_need?: string; priority_score?: number;
};
type Merge = { id: number; source: { title: string }; target: { title: string }; similarity: number; explanation: string };

const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export default function Home() {
  const [items, setItems] = useState<Feature[]>([]);
  const [merges, setMerges] = useState<Merge[]>([]);
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [segment, setSegment] = useState("Unspecified");
  const [message, setMessage] = useState("");
  const [busy, setBusy] = useState(false);

  async function load() {
    const [requests, suggestions] = await Promise.all([
      fetch(API + "/api/requests").then(r => r.json()),
      fetch(API + "/api/merge-suggestions").then(r => r.json())
    ]);
    setItems(requests); setMerges(suggestions);
  }
  useEffect(() => { load().catch(() => setMessage("Could not connect to the API. Start the backend and refresh.")); }, []);

  async function action(path: string, body?: unknown) {
    setBusy(true); setMessage("");
    try {
      const response = await fetch(API + path, { method: "POST", headers: { "Content-Type": "application/json" }, body: body ? JSON.stringify(body) : undefined });
      const data = await response.json();
      if (!response.ok) throw new Error(data.detail || "Request failed");
      setMessage(data.message || "Action completed."); await load(); return data;
    } catch (error) { setMessage(error instanceof Error ? error.message : "Something went wrong."); }
    finally { setBusy(false); }
  }

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    await action("/api/requests", { title, description, customer_segment: segment });
    setTitle(""); setDescription("");
  }

  return <main className="shell">
    <header><div className="brand">✦ FeatureIQ <span>PRODUCT INTELLIGENCE</span></div><span className="status">● MVP workspace</span></header>
    <section className="hero"><div><p className="eyebrow">CUSTOMER SIGNAL → PRODUCT DECISIONS</p><h1>Find the signal in<br/><em>customer feedback.</em></h1><p className="sub">Turn scattered feature requests into clear, evidence-backed product priorities.</p></div><div className="hero-card"><b>AI-assisted triage</b><p>Extract underlying needs, discover similar requests, and create a prioritisation brief.</p><button disabled={busy} onClick={() => action("/api/demo/seed")}>Load demo data</button><button className="secondary" disabled={busy} onClick={() => action("/api/decision-briefs").then(() => setMessage("Decision brief generated."))}>Generate decision brief</button></div></section>
    {message && <p className="notice">{message}</p>}
    <section className="grid">
      <div className="panel"><div className="panel-head"><div><p className="eyebrow">INBOX</p><h2>Feature requests</h2></div><span>{items.length} active</span></div>
        <form onSubmit={submit} className="request-form"><input required minLength={5} placeholder="Feature title" value={title} onChange={e => setTitle(e.target.value)}/><textarea required minLength={15} placeholder="What problem are customers trying to solve?" value={description} onChange={e => setDescription(e.target.value)}/><input placeholder="Customer segment" value={segment} onChange={e => setSegment(e.target.value)}/><button disabled={busy}>Submit request</button></form>
        <div className="request-list">{items.map(item => <article className="request" key={item.id}><div><b>{item.title}</b><p>{item.description}</p><small>{item.customer_segment} · {item.theme || "Not analysed"} · {item.vote_count} votes</small>{item.underlying_need && <blockquote>{item.underlying_need}</blockquote>}</div><div className="row-actions"><strong>{item.priority_score ?? "—"}</strong><button className="small" disabled={busy} onClick={() => action("/api/requests/" + item.id + "/analyse")}>Analyse</button><button className="small ghost" disabled={busy} onClick={() => action("/api/requests/" + item.id + "/vote", { voter_key: "demo-" + item.id })}>Support</button></div></article>)}</div>
      </div>
      <aside className="panel"><p className="eyebrow">HUMAN-IN-THE-LOOP</p><h2>Suggested consolidations</h2><p className="muted">AI suggestions require a product manager's decision. No automatic merges.</p>{merges.length === 0 && <p className="empty">Analyse requests to discover possible duplicates.</p>}{merges.map(m => <article className="merge" key={m.id}><small>{Math.round(m.similarity * 100)}% similarity</small><b>{m.source.title}</b><span>↳ {m.target.title}</span><p>{m.explanation}</p><div><button className="small" onClick={() => action("/api/merge-suggestions/" + m.id + "/decision", { decision: "approve" })}>Approve</button><button className="small ghost" onClick={() => action("/api/merge-suggestions/" + m.id + "/decision", { decision: "reject" })}>Reject</button></div></article>)}</aside>
    </section>
    <footer>FeatureIQ · AI supports decisions; accountable people make them.</footer>
  </main>;
}
