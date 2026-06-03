"use client";

import { useEffect, useState } from "react";

const phrases = [
  "Detect hallucinations.",
  "Verify trusted sources.",
  "Score AI risk.",
  "Build trust in enterprise LLM systems.",
];

const API_BASE = "https://trustguard-ai-production.up.railway.app";

const FEATURE_CARDS = [
  { icon: "◎", title: "Detect", desc: "Identify hallucinations in LLM responses" },
  { icon: "⊡", title: "Verify", desc: "Trace answers to trusted sources" },
  { icon: "⌁", title: "Score", desc: "Assess risk levels automatically" },
  { icon: "◈", title: "Learn", desc: "Collect feedback for future improvement" },
];

const LOGS_PER_PAGE = 5;

export default function Home() {
  const [question, setQuestion] = useState("");
  const [url, setUrl] = useState("");
  const [loading, setLoading] = useState(false);
  const [ingesting, setIngesting] = useState(false);
  const [feedbackStatus, setFeedbackStatus] = useState("");
  const [result, setResult] = useState<any>(null);
  const [ingestResult, setIngestResult] = useState<any>(null);
  const [typedText, setTypedText] = useState("");
  const [phraseIndex, setPhraseIndex] = useState(0);
  const [auditLogs, setAuditLogs] = useState<any[]>([]);
  const [auditLoading, setAuditLoading] = useState(false);
  const [auditPage, setAuditPage] = useState(1);
  const [topQuestions, setTopQuestions] = useState<any[]>([]);
  const [activeTab, setActiveTab] = useState<"sources" | "feedback">("sources");

  useEffect(() => {
    let i = 0;
    const current = phrases[phraseIndex];
    const typing = setInterval(() => {
      setTypedText(current.slice(0, i));
      i++;
      if (i > current.length) {
        clearInterval(typing);
        setTimeout(() => {
          setTypedText("");
          setPhraseIndex((prev) => (prev + 1) % phrases.length);
        }, 1400);
      }
    }, 55);
    return () => clearInterval(typing);
  }, [phraseIndex]);

  const analyzeQuestion = async () => {
    setLoading(true);
    setResult(null);
    setFeedbackStatus("");
    setActiveTab("sources");
    try {
      const res = await fetch(`${API_BASE}/analyze`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question }),
      });
      if (!res.ok) throw new Error();
      setResult(await res.json());
    } catch { alert("Frontend could not connect to backend."); }
    setLoading(false);
  };

  const ingestUrl = async () => {
    setIngesting(true);
    setIngestResult(null);
    try {
      const res = await fetch(`${API_BASE}/ingest-url`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ url }),
      });
      if (!res.ok) throw new Error();
      setIngestResult(await res.json());
    } catch { alert("Could not ingest this URL."); }
    setIngesting(false);
  };

  const submitFeedback = async (feedback: string) => {
    if (!result) return;
    try {
      const res = await fetch(`${API_BASE}/feedback`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question: result.question, answer: result.answer, feedback, corrected_answer: "" }),
      });
      if (!res.ok) throw new Error();
      setFeedbackStatus(`Marked as: ${feedback}`);
    } catch { alert("Could not save feedback."); }
  };

  const loadAuditLogs = async () => {
    setAuditLoading(true);
    try {
      const res = await fetch(`${API_BASE}/audit-logs`);
      if (!res.ok) throw new Error();
      const data = await res.json();
      setAuditLogs(data.logs || []);
      setTopQuestions(data.top_questions || []);
      setAuditPage(1);
    } catch { alert("Could not load audit logs."); }
    setAuditLoading(false);
  };

  const resetQuery = () => { setQuestion(""); setResult(null); setFeedbackStatus(""); };
  const resetUrl = () => { setUrl(""); setIngestResult(null); };
  const closeAuditLogs = () => { setAuditLogs([]); setTopQuestions([]); setAuditPage(1); };

  const hallucination = result?.hallucination_analysis ?? null;
  const riskLevel = result?.risk_analysis?.risk_level;
  const riskStyles: Record<string, { color: string; bg: string; border: string }> = {
    Low:    { color: "#16a34a", bg: "#f0fdf4", border: "#86efac" },
    Medium: { color: "#d97706", bg: "#fffbeb", border: "#fcd34d" },
    High:   { color: "#dc2626", bg: "#fef2f2", border: "#fca5a5" },
  };
  const rs = riskStyles[riskLevel] ?? riskStyles["Low"];

  const sorted = [...auditLogs].sort((a, b) => new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime());
  const totalPages = Math.ceil(sorted.length / LOGS_PER_PAGE);
  const paginated = sorted.slice((auditPage - 1) * LOGS_PER_PAGE, auditPage * LOGS_PER_PAGE);

  return (
    <main style={{ minHeight: "100vh", background: "#f5f4f7", fontFamily: "ui-sans-serif, system-ui, sans-serif", color: "#1a1523" }}>
      <style jsx>{`
        * { box-sizing: border-box; }

        .card {
          background: #fff;
          border: 1px solid #e8e4f2;
          border-radius: 14px;
          padding: 20px;
        }
        .card-accent {
          background: #fff;
          border: 1.5px solid #c4b5fd;
          border-radius: 14px;
          padding: 20px;
          box-shadow: 0 2px 16px rgba(124,58,237,.1);
        }

        .lbl {
          font-size: 10px;
          font-weight: 700;
          letter-spacing: .1em;
          text-transform: uppercase;
          color: #a78bfa;
          margin-bottom: 10px;
        }

        input, textarea {
          width: 100%;
          padding: 10px 13px;
          border: 1px solid #e5e7eb;
          border-radius: 8px;
          font-size: 14px;
          background: #fafafa;
          color: #1a1523;
          outline: none;
          font-family: inherit;
          margin-bottom: 8px;
          transition: border-color .15s, box-shadow .15s;
        }
        input::placeholder, textarea::placeholder { color: #c4b5fd; }
        input:focus, textarea:focus {
          border-color: #a78bfa;
          background: #fff;
          box-shadow: 0 0 0 3px rgba(124,58,237,.1);
        }

        .btn-primary {
          background: #7c3aed;
          color: #fff;
          border: none;
          border-radius: 8px;
          padding: 10px 16px;
          font-size: 14px;
          font-weight: 600;
          cursor: pointer;
          width: 100%;
          margin-bottom: 8px;
          box-shadow: 0 2px 12px rgba(124,58,237,.25);
          transition: background .15s, box-shadow .15s;
        }
        .btn-primary:hover:not(:disabled) { background: #6d28d9; box-shadow: 0 4px 18px rgba(124,58,237,.35); }
        .btn-primary:disabled { opacity: .45; cursor: not-allowed; }

        .btn-ghost {
          background: #fff;
          color: #6b7280;
          border: 1px solid #e5e7eb;
          border-radius: 8px;
          padding: 10px 16px;
          font-size: 14px;
          cursor: pointer;
          width: 100%;
          transition: border-color .15s, color .15s, background .15s;
        }
        .btn-ghost:hover { border-color: #a78bfa; color: #7c3aed; background: #faf5ff; }
        .btn-ghost:disabled { opacity: .35; cursor: not-allowed; }

        .btn-sm { padding: 6px 14px; font-size: 13px; width: auto; }

        .nav { display: flex; justify-content: space-between; align-items: center; padding: 24px 0 40px; }
        .logo { font-weight: 900; font-size: 18px; letter-spacing: -.03em; color: #1a1523; }
        .logo-accent { color: #7c3aed; }
        .nav-contact {
          border: 1px solid #d4c9f0;
          background: #fff;
          color: #7c3aed;
          border-radius: 8px;
          padding: 7px 18px;
          font-size: 13px;
          font-weight: 500;
          cursor: pointer;
          text-decoration: none;
          transition: background .15s, border-color .15s;
        }
        .nav-contact:hover { background: #f3effe; border-color: #7c3aed; }

        .hero-tag {
          display: inline-block;
          font-size: 10px;
          font-weight: 700;
          letter-spacing: .1em;
          text-transform: uppercase;
          color: #7c3aed;
          background: #ede9fe;
          border: 1px solid #c4b5fd;
          padding: 4px 12px;
          border-radius: 999px;
          margin-bottom: 18px;
        }

        .terminal {
          background: #fff;
          border: 1px solid #e5e0f5;
          border-radius: 10px;
          padding: 13px 18px;
          margin-bottom: 36px;
          box-shadow: 0 1px 8px rgba(124,58,237,.07);
          display: flex;
          align-items: center;
          gap: 10px;
        }
        .typing-text { font-size: 16px; font-family: ui-monospace, monospace; color: #1a1523; font-weight: 500; min-height: 26px; }
        .cursor { animation: blink .8s infinite; color: #7c3aed; }
        @keyframes blink { 50% { opacity: 0; } }

        .feature-grid { display: grid; grid-template-columns: repeat(4,1fr); gap: 12px; margin-bottom: 36px; }
        @media (max-width: 900px) { .feature-grid { grid-template-columns: repeat(2,1fr); } }
        @media (max-width: 540px) { .feature-grid { grid-template-columns: 1fr; } }

        .feat-card {
          background: #fff;
          border: 1px solid #ede9fe;
          border-radius: 12px;
          padding: 18px;
          transition: border-color .2s, box-shadow .2s;
        }
        .feat-card:hover { border-color: #a78bfa; box-shadow: 0 2px 12px rgba(124,58,237,.1); }
        .feat-icon { font-size: 18px; color: #7c3aed; margin-bottom: 8px; }
        .feat-title { font-size: 13px; font-weight: 700; color: #1a1523; margin-bottom: 3px; }
        .feat-desc { font-size: 12px; color: #9ca3af; line-height: 1.5; }

        .main-grid { display: grid; grid-template-columns: 320px 1fr; gap: 16px; margin-bottom: 36px; align-items: start; }
        @media (max-width: 860px) { .main-grid { grid-template-columns: 1fr; } }

        .risk-badge {
          display: inline-block;
          padding: 3px 12px;
          border-radius: 999px;
          font-size: 12px;
          font-weight: 700;
          border: 1px solid;
        }

        .meta-row {
          display: grid;
          grid-template-columns: 1fr 1px 1fr;
          background: #faf9ff;
          border: 1px solid #ede9fe;
          border-radius: 8px;
          margin-top: 14px;
          overflow: hidden;
        }
        .meta-col { padding: 12px 14px; }
        .meta-div { background: #ede9fe; }
        .meta-label { font-size: 9px; font-weight: 700; letter-spacing: .08em; text-transform: uppercase; color: #a78bfa; margin-bottom: 4px; }
        .meta-val { font-size: 14px; font-weight: 700; color: #1a1523; }
        .meta-sub { font-size: 11px; color: #9ca3af; margin-top: 2px; line-height: 1.4; }

        .tabs { display: flex; gap: 6px; margin-bottom: 14px; }
        .tab {
          border: 1px solid #e5e7eb;
          background: #fff;
          border-radius: 6px;
          padding: 5px 14px;
          font-size: 12px;
          cursor: pointer;
          color: #9ca3af;
          font-weight: 500;
          transition: .15s;
        }
        .tab.active { background: #ede9fe; border-color: #c4b5fd; color: #7c3aed; }

        .source-item {
          display: flex;
          flex-direction: column;
          gap: 2px;
          padding: 10px 13px;
          border: 1px solid #e8e4f2;
          border-radius: 8px;
          background: #fafafa;
          text-decoration: none;
          transition: border-color .15s, background .15s;
          margin-bottom: 7px;
        }
        .source-item:last-child { margin-bottom: 0; }
        .source-item:hover { border-color: #a78bfa; background: #faf5ff; }
        .source-title { font-size: 13px; color: #374151; }
        .source-url { font-size: 11px; color: #7c3aed; }

        .fb-btn {
          border: 1px solid #e5e7eb;
          background: #fff;
          border-radius: 8px;
          padding: 8px 16px;
          font-size: 13px;
          font-weight: 600;
          cursor: pointer;
          color: #6b7280;
          transition: .15s;
        }
        .fb-btn.correct:hover { background: #f0fdf4; border-color: #16a34a; color: #16a34a; }
        .fb-btn.partial:hover { background: #fffbeb; border-color: #d97706; color: #d97706; }
        .fb-btn.wrong:hover   { background: #fef2f2; border-color: #dc2626; color: #dc2626; }

        .sec-title { font-size: 13px; font-weight: 700; color: #374151; margin-bottom: 12px; }

        .audit-th {
          text-align: left;
          padding: 8px 12px;
          color: #9ca3af;
          font-size: 10px;
          letter-spacing: .07em;
          text-transform: uppercase;
          border-bottom: 1px solid #f3f4f6;
          font-weight: 600;
        }
        .audit-td { padding: 10px 12px; color: #374151; font-size: 13px; border-bottom: 1px solid #f9fafb; vertical-align: top; }

        .faq-track { display: inline-flex; gap: 10px; animation: scrollFaq 80s linear infinite; }
        .faq-pill {
          display: inline-flex;
          align-items: center;
          gap: 10px;
          padding: 8px 16px;
          border-radius: 999px;
          border: 1px solid #ede9fe;
          background: #fff;
          font-size: 13px;
          color: #374151;
          white-space: nowrap;
        }
        .faq-count { color: #7c3aed; font-size: 12px; font-weight: 700; }
        @keyframes scrollFaq { from { transform: translateX(0); } to { transform: translateX(-50%); } }

        .empty-state {
          min-height: 300px;
          display: flex;
          flex-direction: column;
          align-items: center;
          justify-content: center;
          text-align: center;
          gap: 10px;
        }
      `}</style>

      <div style={{ maxWidth: 1100, margin: "0 auto", padding: "0 24px" }}>

        {/* Nav */}
        <nav className="nav">
          <span className="logo">Trust<span className="logo-accent">Guard</span> AI</span>
          <a href="mailto:m.haseeb311@gmail.com" className="nav-contact">Contact</a>
        </nav>

        {/* Hero */}
        <section style={{ marginBottom: 36 }}>
          <div className="hero-tag">● AI Governance Platform</div>
          <h1 style={{ fontSize: 44, fontWeight: 900, letterSpacing: "-.04em", lineHeight: 1.05, marginBottom: 14 }}>
            Engineering trust<br />
            in every <span style={{ color: "#7c3aed" }}>AI response.</span>
          </h1>
          <p style={{ fontSize: 16, color: "#6b7280", maxWidth: 540, marginBottom: 24, lineHeight: 1.7 }}>
            Detect hallucinations, verify sources, score risk, and create audit-ready governance workflows for enterprise LLM systems.
          </p>
          <div className="terminal">
            <span style={{ color: "#a78bfa", fontFamily: "monospace", fontSize: 15 }}>›</span>
            <span className="typing-text">
              {typedText}<span className="cursor">|</span>
            </span>
          </div>
        </section>

        {/* Feature cards */}
        <div className="feature-grid">
          {FEATURE_CARDS.map(({ icon, title, desc }) => (
            <div className="feat-card" key={title}>
              <div className="feat-icon">{icon}</div>
              <div className="feat-title">{title}</div>
              <div className="feat-desc">{desc}</div>
            </div>
          ))}
        </div>

        {/* Main panel */}
        <div className="main-grid">

          {/* Left */}
          <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
            <div className="card">
              <p className="lbl">Knowledge Source</p>
              <input value={url} onChange={(e) => setUrl(e.target.value)} placeholder="https://example.gov/policy" />
              <button onClick={ingestUrl} disabled={ingesting || !url} className="btn-primary">
                {ingesting ? "Ingesting…" : "Ingest URL"}
              </button>
              <button onClick={resetUrl} className="btn-ghost">Clear</button>
              {ingestResult && (
                <div style={{ marginTop: 10, padding: "10px 13px", background: "#f0fdf4", border: "1px solid #86efac", borderRadius: 8, fontSize: 13, color: "#16a34a" }}>
                  {ingestResult.status} — {ingestResult.chunks_added || 0} chunks added
                </div>
              )}
            </div>

            <div className="card">
              <p className="lbl">Ask a Question</p>
              <textarea value={question} onChange={(e) => setQuestion(e.target.value)} rows={7} placeholder="Ask a governance, policy, or compliance question…" style={{ resize: "vertical" }} />
              <button onClick={analyzeQuestion} disabled={loading || !question} className="btn-primary">
                {loading ? "Analyzing…" : "Analyze Query"}
              </button>
              <button onClick={resetQuery} className="btn-ghost">Clear</button>
            </div>
          </div>

          {/* Right */}
          <div>
            {!result ? (
              <div className="card empty-state">
                <div style={{ fontSize: 30, color: "#c4b5fd" }}>◎</div>
                <div style={{ fontWeight: 700, color: "#6b7280", fontSize: 15 }}>Ready for analysis</div>
                <div style={{ fontSize: 13, color: "#9ca3af", maxWidth: 260, lineHeight: 1.6 }}>
                  Ask a question to see a grounded answer, hallucination score, risk level, and sources.
                </div>
              </div>
            ) : (
              <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>

                {/* Answer */}
                <div className="card-accent">
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 12 }}>
                    <p className="lbl" style={{ marginBottom: 0 }}>AI Answer</p>
                    <span className="risk-badge" style={{ color: rs.color, background: rs.bg, borderColor: rs.border }}>
                      {riskLevel} Risk
                    </span>
                  </div>
                  <p style={{ fontSize: 15, lineHeight: 1.75, color: "#374151", margin: 0 }}>{result.answer}</p>
                  <div className="meta-row">
                    <div className="meta-col">
                      <div className="meta-label">Hallucination Score</div>
                      <div className="meta-val">{hallucination?.hallucination_score ?? "—"}</div>
                      <div className="meta-sub">{hallucination?.reason}</div>
                    </div>
                    <div className="meta-div" />
                    <div className="meta-col">
                      <div className="meta-label">Risk Status</div>
                      <div className="meta-val" style={{ color: rs.color }}>{result.risk_analysis?.risk_status}</div>
                      <div className="meta-sub">{result.risk_analysis?.risk_reason}</div>
                    </div>
                  </div>
                </div>

                {/* Sources + Feedback tabs */}
                <div className="card">
                  <div className="tabs">
                    <button className={`tab${activeTab === "sources" ? " active" : ""}`} onClick={() => setActiveTab("sources")}>
                      Sources
                    </button>
                    <button className={`tab${activeTab === "feedback" ? " active" : ""}`} onClick={() => setActiveTab("feedback")}>
                      Feedback
                    </button>
                  </div>

                  {activeTab === "sources" && (
                    <div>
                      {result.sources?.length > 0 ? (
                        result.sources.map((src: any, i: number) => (
                          <a key={i} href={src.url} target="_blank" className="source-item">
                            <span className="source-title">{i + 1}. {src.title || "No Title"}</span>
                            <span className="source-url">{src.url}</span>
                          </a>
                        ))
                      ) : (
                        <p style={{ fontSize: 13, color: "#9ca3af", margin: 0 }}>No sources retrieved.</p>
                      )}
                    </div>
                  )}

                  {activeTab === "feedback" && (
                    <div>
                      <p className="sec-title">Was this answer useful?</p>
                      <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
                        <button className="fb-btn correct" onClick={() => submitFeedback("Correct")}>✓ Correct</button>
                        <button className="fb-btn partial" onClick={() => submitFeedback("Partially Correct")}>~ Partially Correct</button>
                        <button className="fb-btn wrong" onClick={() => submitFeedback("Incorrect")}>✕ Incorrect</button>
                      </div>
                      {feedbackStatus && <p style={{ marginTop: 10, marginBottom: 0, fontSize: 13, color: "#7c3aed" }}>{feedbackStatus}</p>}
                    </div>
                  )}
                </div>

              </div>
            )}
          </div>
        </div>

        {/* FAQ marquee */}
        {topQuestions.length > 0 && (
          <div className="card" style={{ marginBottom: 16, overflow: "hidden" }}>
            <p className="sec-title">Frequently Asked Questions</p>
            <div style={{ overflow: "hidden", whiteSpace: "nowrap" }}>
              <div className="faq-track">
                {[...topQuestions, ...topQuestions].map((item: any, i: number) => (
                  <div key={i} className="faq-pill">
                    <span>{item.question}</span>
                    <span className="faq-count">{item.count}×</span>
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}

        {/* Audit log */}
        <div className="card" style={{ marginBottom: 48 }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 16 }}>
            <p className="sec-title" style={{ marginBottom: 0 }}>Audit Log</p>
            <div style={{ display: "flex", gap: 8 }}>
              <button onClick={loadAuditLogs} className="btn-primary btn-sm">{auditLoading ? "Loading…" : "Load Logs"}</button>
              <button onClick={closeAuditLogs} className="btn-ghost btn-sm">Clear</button>
            </div>
          </div>

          {auditLogs.length === 0 ? (
            <p style={{ color: "#9ca3af", fontSize: 13, margin: 0 }}>No audit logs loaded.</p>
          ) : (
            <>
              <div style={{ overflowX: "auto" }}>
                <table style={{ width: "100%", borderCollapse: "collapse" }}>
                  <thead>
                    <tr>
                      <th className="audit-th">Time</th>
                      <th className="audit-th">Question</th>
                      <th className="audit-th">Risk</th>
                      <th className="audit-th">Reason</th>
                    </tr>
                  </thead>
                  <tbody>
                    {paginated.map((log: any, i: number) => {
                      const s = riskStyles[log.risk_level] ?? riskStyles["Low"];
                      return (
                        <tr key={i}>
                          <td className="audit-td" style={{ whiteSpace: "nowrap", color: "#9ca3af", fontSize: 12 }}>{log.timestamp}</td>
                          <td className="audit-td">{log.query}</td>
                          <td className="audit-td">
                            <span style={{ display: "inline-block", padding: "3px 10px", borderRadius: 999, fontSize: 12, fontWeight: 700, color: s.color, background: s.bg, border: `1px solid ${s.border}` }}>
                              {log.risk_level}
                            </span>
                          </td>
                          <td className="audit-td" style={{ color: "#6b7280" }}>{log.risk_reason}</td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginTop: 14 }}>
                <button className="btn-ghost btn-sm" disabled={auditPage === 1} onClick={() => setAuditPage(auditPage - 1)}>← Previous</button>
                <span style={{ fontSize: 13, color: "#9ca3af" }}>Page {auditPage} of {totalPages || 1}</span>
                <button className="btn-ghost btn-sm" disabled={auditPage >= totalPages} onClick={() => setAuditPage(auditPage + 1)}>Next →</button>
              </div>
            </>
          )}
        </div>

      </div>
    </main>
  );
}
