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
    try {
      const response = await fetch(`${API_BASE}/analyze`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question }),
      });
      if (!response.ok) throw new Error("API error");
      setResult(await response.json());
    } catch {
      alert("Frontend could not connect to backend.");
    }
    setLoading(false);
  };

  const ingestUrl = async () => {
    setIngesting(true);
    setIngestResult(null);
    try {
      const response = await fetch(`${API_BASE}/ingest-url`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ url }),
      });
      if (!response.ok) throw new Error("API error");
      setIngestResult(await response.json());
    } catch {
      alert("Could not ingest this URL.");
    }
    setIngesting(false);
  };

  const submitFeedback = async (feedback: string) => {
    if (!result) return;
    try {
      const response = await fetch(`${API_BASE}/feedback`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          question: result.question,
          answer: result.answer,
          feedback,
          corrected_answer: "",
        }),
      });
      if (!response.ok) throw new Error("Feedback API error");
      setFeedbackStatus(`Marked as: ${feedback}`);
    } catch {
      alert("Could not save feedback.");
    }
  };

  const loadAuditLogs = async () => {
    setAuditLoading(true);
    try {
      const response = await fetch(`${API_BASE}/audit-logs`);
      if (!response.ok) throw new Error("Audit API error");
      const data = await response.json();
      setAuditLogs(data.logs || []);
      setTopQuestions(data.top_questions || []);
      setAuditPage(1);
    } catch {
      alert("Could not load audit logs.");
    }
    setAuditLoading(false);
  };

  const resetQuery = () => { setQuestion(""); setResult(null); setFeedbackStatus(""); };
  const resetUrl = () => { setUrl(""); setIngestResult(null); };
  const closeAuditLogs = () => { setAuditLogs([]); setTopQuestions([]); setAuditPage(1); };

  const hallucination = result?.hallucination_analysis ?? null;
  const riskLevel = result?.risk_analysis?.risk_level;
  const riskColor =
    riskLevel === "Low" ? "#16a34a" : riskLevel === "Medium" ? "#d97706" : "#dc2626";
  const riskBg =
    riskLevel === "Low" ? "#f0fdf4" : riskLevel === "Medium" ? "#fffbeb" : "#fef2f2";

  const sortedAuditLogs = [...auditLogs].sort(
    (a, b) => new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime()
  );
  const totalAuditPages = Math.ceil(sortedAuditLogs.length / LOGS_PER_PAGE);
  const paginatedAuditLogs = sortedAuditLogs.slice(
    (auditPage - 1) * LOGS_PER_PAGE,
    auditPage * LOGS_PER_PAGE
  );

  return (
    <main style={{ minHeight: "100vh", background: "#f8f9fb", fontFamily: "ui-sans-serif, system-ui, sans-serif", color: "#111" }}>
      <style jsx>{`
        * { box-sizing: border-box; }

        .card {
          background: #fff;
          border: 1px solid #e5e7eb;
          border-radius: 12px;
          padding: 24px;
        }

        .label {
          font-size: 11px;
          font-weight: 600;
          letter-spacing: 0.08em;
          text-transform: uppercase;
          color: #6b7280;
          margin-bottom: 8px;
        }

        input, textarea {
          width: 100%;
          padding: 10px 14px;
          border: 1px solid #d1d5db;
          border-radius: 8px;
          font-size: 14px;
          background: #fafafa;
          color: #111;
          outline: none;
          font-family: inherit;
          transition: border-color 0.15s;
        }
        input:focus, textarea:focus {
          border-color: #6366f1;
          background: #fff;
        }

        .btn-primary {
          background: #6366f1;
          color: #fff;
          border: none;
          border-radius: 8px;
          padding: 10px 18px;
          font-size: 14px;
          font-weight: 500;
          cursor: pointer;
          width: 100%;
          transition: background 0.15s;
        }
        .btn-primary:hover:not(:disabled) { background: #4f46e5; }
        .btn-primary:disabled { opacity: 0.5; cursor: not-allowed; }

        .btn-ghost {
          background: transparent;
          color: #6b7280;
          border: 1px solid #e5e7eb;
          border-radius: 8px;
          padding: 10px 18px;
          font-size: 14px;
          cursor: pointer;
          width: 100%;
          transition: border-color 0.15s, color 0.15s;
        }
        .btn-ghost:hover { border-color: #6366f1; color: #6366f1; }
        .btn-ghost:disabled { opacity: 0.4; cursor: not-allowed; }

        .btn-sm {
          padding: 6px 14px;
          font-size: 13px;
          width: auto;
        }

        .divider { height: 1px; background: #f0f0f0; margin: 0; }

        .badge {
          display: inline-block;
          padding: 3px 10px;
          border-radius: 999px;
          font-size: 12px;
          font-weight: 600;
        }

        .section-title {
          font-size: 13px;
          font-weight: 600;
          color: #374151;
          margin: 0 0 16px 0;
        }

        .feedback-btn {
          border: 1px solid #e5e7eb;
          background: #fff;
          border-radius: 8px;
          padding: 8px 16px;
          font-size: 13px;
          cursor: pointer;
          transition: all 0.15s;
          font-weight: 500;
        }
        .feedback-btn.correct:hover { border-color: #16a34a; color: #16a34a; background: #f0fdf4; }
        .feedback-btn.partial:hover { border-color: #d97706; color: #d97706; background: #fffbeb; }
        .feedback-btn.incorrect:hover { border-color: #dc2626; color: #dc2626; background: #fef2f2; }

        .source-item {
          display: flex;
          flex-direction: column;
          gap: 2px;
          padding: 10px 12px;
          border: 1px solid #e5e7eb;
          border-radius: 8px;
          text-decoration: none;
          color: #111;
          font-size: 13px;
          transition: border-color 0.15s;
        }
        .source-item:hover { border-color: #6366f1; }
        .source-url { color: #6366f1; font-size: 11px; }

        .audit-table { width: 100%; border-collapse: collapse; font-size: 13px; }
        .audit-table th { text-align: left; padding: 8px 12px; color: #6b7280; font-weight: 500; border-bottom: 1px solid #e5e7eb; }
        .audit-table td { padding: 10px 12px; border-bottom: 1px solid #f3f4f6; color: #374151; vertical-align: top; }

        .faq-track {
          display: inline-flex;
          gap: 12px;
          animation: scrollFaq 80s linear infinite;
        }
        .faq-pill {
          display: inline-flex;
          align-items: center;
          gap: 10px;
          padding: 8px 16px;
          border-radius: 999px;
          border: 1px solid #e5e7eb;
          background: #fff;
          font-size: 13px;
          color: #374151;
          white-space: nowrap;
        }
        .faq-count { color: #6366f1; font-size: 12px; font-weight: 600; }

        @keyframes scrollFaq {
          from { transform: translateX(0); }
          to { transform: translateX(-50%); }
        }

        .typing-line {
          font-size: 20px;
          font-weight: 500;
          color: #111;
          min-height: 32px;
          font-family: ui-monospace, monospace;
        }
        .cursor { animation: blink 0.8s infinite; color: #6366f1; }
        @keyframes blink { 50% { opacity: 0; } }

        .nav { display: flex; justify-content: space-between; align-items: center; padding: 20px 0 40px; }
        .nav-logo { font-weight: 700; font-size: 18px; letter-spacing: -0.02em; }
        .nav-contact {
          border: 1px solid #d1d5db;
          background: #fff;
          color: #374151;
          border-radius: 8px;
          padding: 8px 18px;
          font-size: 13px;
          font-weight: 500;
          cursor: pointer;
          text-decoration: none;
          transition: border-color 0.15s;
        }
        .nav-contact:hover { border-color: #6366f1; color: #6366f1; }

        .hero-tag {
          display: inline-block;
          font-size: 11px;
          font-weight: 600;
          letter-spacing: 0.1em;
          text-transform: uppercase;
          color: #6366f1;
          background: #eef2ff;
          padding: 4px 12px;
          border-radius: 999px;
          margin-bottom: 20px;
        }

        .feature-grid {
          display: grid;
          grid-template-columns: repeat(4, 1fr);
          gap: 12px;
          margin-bottom: 40px;
        }
        @media (max-width: 900px) { .feature-grid { grid-template-columns: repeat(2, 1fr); } }
        @media (max-width: 540px) { .feature-grid { grid-template-columns: 1fr; } }

        .feature-card {
          background: #fff;
          border: 1px solid #e5e7eb;
          border-radius: 10px;
          padding: 18px;
        }
        .feature-icon { font-size: 20px; color: #6366f1; margin-bottom: 8px; }
        .feature-title { font-size: 13px; font-weight: 600; color: #111; margin-bottom: 4px; }
        .feature-desc { font-size: 12px; color: #9ca3af; }

        .main-grid {
          display: grid;
          grid-template-columns: 380px 1fr;
          gap: 20px;
          margin-bottom: 40px;
        }
        @media (max-width: 860px) { .main-grid { grid-template-columns: 1fr; } }

        .result-meta {
          display: flex;
          gap: 16px;
          padding: 16px 20px;
          background: #fafafa;
          border-radius: 8px;
          border: 1px solid #e5e7eb;
          margin-top: 16px;
        }
        .meta-item { flex: 1; }
        .meta-label { font-size: 11px; text-transform: uppercase; letter-spacing: 0.06em; color: #9ca3af; font-weight: 600; margin-bottom: 4px; }
        .meta-value { font-size: 14px; font-weight: 600; color: #111; }
        .meta-sub { font-size: 12px; color: #6b7280; margin-top: 2px; }
      `}</style>

      <div style={{ maxWidth: 1100, margin: "0 auto", padding: "0 24px" }}>

        {/* Nav */}
        <nav className="nav">
          <span className="nav-logo">TrustGuard AI</span>
          <a href="mailto:m.haseeb311@gmail.com" className="nav-contact">Contact</a>
        </nav>

        {/* Hero */}
        <section style={{ marginBottom: 40 }}>
          <div className="hero-tag">AI Governance Platform</div>
          <h1 style={{ fontSize: 42, fontWeight: 800, letterSpacing: "-0.03em", lineHeight: 1.1, marginBottom: 16 }}>
            Engineering trust<br />
            in every <span style={{ color: "#6366f1" }}>AI response.</span>
          </h1>
          <p style={{ fontSize: 16, color: "#6b7280", maxWidth: 560, marginBottom: 24, lineHeight: 1.6 }}>
            Detect hallucinations, verify sources, score AI risk, and create audit-ready governance workflows for enterprise LLM systems.
          </p>
          <div style={{ background: "#fff", border: "1px solid #e5e7eb", borderRadius: 10, padding: "14px 20px" }}>
            <span style={{ color: "#9ca3af", fontFamily: "ui-monospace, monospace", fontSize: 13, marginRight: 8 }}>›</span>
            <span className="typing-line">
              {typedText}<span className="cursor">|</span>
            </span>
          </div>
        </section>

        {/* Feature cards */}
        <div className="feature-grid">
          {FEATURE_CARDS.map(({ icon, title, desc }) => (
            <div className="feature-card" key={title}>
              <div className="feature-icon">{icon}</div>
              <div className="feature-title">{title}</div>
              <div className="feature-desc">{desc}</div>
            </div>
          ))}
        </div>

        {/* Main panel */}
        <div className="main-grid">

          {/* Left: inputs */}
          <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>

            {/* Ingest */}
            <div className="card">
              <p className="label">Knowledge Source</p>
              <input
                value={url}
                onChange={(e) => setUrl(e.target.value)}
                placeholder="https://example.gov/policy"
                style={{ marginBottom: 10 }}
              />
              <button onClick={ingestUrl} disabled={ingesting || !url} className="btn-primary" style={{ marginBottom: 8 }}>
                {ingesting ? "Ingesting…" : "Ingest URL"}
              </button>
              <button onClick={resetUrl} className="btn-ghost">Clear</button>
              {ingestResult && (
                <div style={{ marginTop: 12, padding: "10px 14px", background: "#f0fdf4", border: "1px solid #bbf7d0", borderRadius: 8, fontSize: 13, color: "#16a34a" }}>
                  {ingestResult.status} — {ingestResult.chunks_added || 0} chunks added
                </div>
              )}
            </div>

            {/* Query */}
            <div className="card">
              <p className="label">Ask a Question</p>
              <textarea
                value={question}
                onChange={(e) => setQuestion(e.target.value)}
                rows={7}
                placeholder="Ask a governance, policy, or compliance question…"
                style={{ marginBottom: 10, resize: "vertical" }}
              />
              <button onClick={analyzeQuestion} disabled={loading || !question} className="btn-primary" style={{ marginBottom: 8 }}>
                {loading ? "Analyzing…" : "Analyze Query"}
              </button>
              <button onClick={resetQuery} className="btn-ghost">Clear</button>
            </div>
          </div>

          {/* Right: results */}
          <div>
            {!result ? (
              <div className="card" style={{ height: "100%", display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", textAlign: "center", padding: 48, color: "#9ca3af" }}>
                <div style={{ fontSize: 32, marginBottom: 12 }}>◎</div>
                <div style={{ fontWeight: 600, color: "#374151", marginBottom: 6 }}>Ready for analysis</div>
                <div style={{ fontSize: 14 }}>Ask a question to see the grounded answer, hallucination score, risk level, and sources.</div>
              </div>
            ) : (
              <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>

                {/* Answer + meta */}
                <div className="card">
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 14 }}>
                    <p className="label" style={{ marginBottom: 0 }}>AI Answer</p>
                    <span className="badge" style={{ background: riskBg, color: riskColor }}>{riskLevel} Risk</span>
                  </div>
                  <p style={{ fontSize: 15, lineHeight: 1.7, color: "#111", margin: 0 }}>{result.answer}</p>

                  {/* Hallucination + Risk inline */}
                  <div className="result-meta">
                    <div className="meta-item">
                      <div className="meta-label">Hallucination Score</div>
                      <div className="meta-value">{hallucination?.hallucination_score ?? "—"}</div>
                      <div className="meta-sub">{hallucination?.reason}</div>
                    </div>
                    <div style={{ width: 1, background: "#e5e7eb" }} />
                    <div className="meta-item">
                      <div className="meta-label">Risk Status</div>
                      <div className="meta-value" style={{ color: riskColor }}>{result.risk_analysis?.risk_status}</div>
                      <div className="meta-sub">{result.risk_analysis?.risk_reason}</div>
                    </div>
                  </div>
                </div>

                {/* Sources */}
                {result.sources?.length > 0 && (
                  <div className="card">
                    <p className="section-title">Retrieved Sources</p>
                    <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
                      {result.sources.map((source: any, i: number) => (
                        <a key={i} href={source.url} target="_blank" className="source-item">
                          <span>{i + 1}. {source.title || "No Title"}</span>
                          <span className="source-url">{source.url}</span>
                        </a>
                      ))}
                    </div>
                  </div>
                )}

                {/* Feedback */}
                <div className="card">
                  <p className="section-title" style={{ marginBottom: 12 }}>Was this answer useful?</p>
                  <div style={{ display: "flex", gap: 8 }}>
                    <button className="feedback-btn correct" onClick={() => submitFeedback("Correct")}>✓ Correct</button>
                    <button className="feedback-btn partial" onClick={() => submitFeedback("Partially Correct")}>~ Partially Correct</button>
                    <button className="feedback-btn incorrect" onClick={() => submitFeedback("Incorrect")}>✕ Incorrect</button>
                  </div>
                  {feedbackStatus && (
                    <p style={{ marginTop: 10, marginBottom: 0, fontSize: 13, color: "#6366f1" }}>{feedbackStatus}</p>
                  )}
                </div>

              </div>
            )}
          </div>
        </div>

        {/* FAQ marquee */}
        {topQuestions.length > 0 && (
          <div className="card" style={{ marginBottom: 20, overflow: "hidden" }}>
            <p className="section-title">Frequently Asked Questions</p>
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

        {/* Audit logs */}
        <div className="card" style={{ marginBottom: 40 }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 16 }}>
            <p className="section-title" style={{ marginBottom: 0 }}>Audit Log</p>
            <div style={{ display: "flex", gap: 8 }}>
              <button onClick={loadAuditLogs} className="btn-primary btn-sm">
                {auditLoading ? "Loading…" : "Load Logs"}
              </button>
              <button onClick={closeAuditLogs} className="btn-ghost btn-sm">Clear</button>
            </div>
          </div>

          {auditLogs.length === 0 ? (
            <p style={{ color: "#9ca3af", fontSize: 13, margin: 0 }}>No audit logs loaded.</p>
          ) : (
            <>
              <div style={{ overflowX: "auto" }}>
                <table className="audit-table">
                  <thead>
                    <tr>
                      <th>Time</th>
                      <th>Question</th>
                      <th>Risk</th>
                      <th>Reason</th>
                    </tr>
                  </thead>
                  <tbody>
                    {paginatedAuditLogs.map((log: any, i: number) => (
                      <tr key={i}>
                        <td style={{ whiteSpace: "nowrap", color: "#9ca3af" }}>{log.timestamp}</td>
                        <td>{log.query}</td>
                        <td>
                          <span className="badge" style={{
                            background: log.risk_level === "Low" ? "#f0fdf4" : log.risk_level === "Medium" ? "#fffbeb" : "#fef2f2",
                            color: log.risk_level === "Low" ? "#16a34a" : log.risk_level === "Medium" ? "#d97706" : "#dc2626"
                          }}>
                            {log.risk_level}
                          </span>
                        </td>
                        <td style={{ color: "#6b7280" }}>{log.risk_reason}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>

              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginTop: 16 }}>
                <button className="btn-ghost btn-sm" disabled={auditPage === 1} onClick={() => setAuditPage(auditPage - 1)}>← Previous</button>
                <span style={{ fontSize: 13, color: "#9ca3af" }}>Page {auditPage} of {totalAuditPages || 1}</span>
                <button className="btn-ghost btn-sm" disabled={auditPage >= totalAuditPages} onClick={() => setAuditPage(auditPage + 1)}>Next →</button>
              </div>
            </>
          )}
        </div>

      </div>
    </main>
  );
}
