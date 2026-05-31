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
  ["◎", "Detect", "Identify hallucinations in LLM responses"],
  ["盾", "Verify", "Trace answers to trusted sources"],
  ["⌁", "Score", "Assess risk levels automatically"],
  ["🔒", "Learn", "Collect feedback for future improvement"],
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

  // ── Typing animation ─────────────────────────────────────────────────────────
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
        }, 1200);
      }
    }, 55);

    return () => clearInterval(typing);
  }, [phraseIndex]);

  // ── API helpers ───────────────────────────────────────────────────────────────
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

      const data = await response.json();
      setResult(data);
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

      const data = await response.json();
      setIngestResult(data);
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

      setFeedbackStatus(`Feedback saved: ${feedback}`);
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

  // ── Reset helpers ─────────────────────────────────────────────────────────────
  const resetQuery = () => {
    setQuestion("");
    setResult(null);
    setFeedbackStatus("");
  };

  const resetUrl = () => {
    setUrl("");
    setIngestResult(null);
  };

  const closeAuditLogs = () => {
    setAuditLogs([]);
    setTopQuestions([]);
    setAuditPage(1);
  };

  // ── Derived values ────────────────────────────────────────────────────────────
  const hallucination = result?.hallucination_analysis ?? null;
  const riskLevel = result?.risk_analysis?.risk_level;
  const riskBadge =
    riskLevel === "Low"
      ? "success"
      : riskLevel === "Medium"
        ? "warning"
        : "danger";

  const sortedAuditLogs = [...auditLogs].sort(
    (a, b) => new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime(),
  );
  const totalAuditPages = Math.ceil(sortedAuditLogs.length / LOGS_PER_PAGE);
  const paginatedAuditLogs = sortedAuditLogs.slice(
    (auditPage - 1) * LOGS_PER_PAGE,
    auditPage * LOGS_PER_PAGE,
  );

  // ── Render ────────────────────────────────────────────────────────────────────
  return (
    <main className="min-vh-100 text-light app-bg">
      <style jsx>{`
        /* ── Design tokens ── */
        :root {
          --bg-base:       #0f0e0c;
          --bg-surface:    #1a1814;
          --bg-card:       rgba(26, 24, 20, 0.92);
          --border:        rgba(255, 220, 120, 0.08);
          --border-accent: rgba(217, 160, 50, 0.4);
          --accent:        #d9a032;
          --accent-dark:   #b8862a;
          --accent-dim:    rgba(217, 160, 50, 0.1);
          --text-primary:  #ede8df;
          --text-muted:    #7a7168;
          --text-heading:  #faf7f2;
          --glow:          rgba(217, 160, 50, 0.1);
        }

        /* ── Base ── */
        .app-bg {
          background:
            radial-gradient(
              ellipse at 15% 0%,
              rgba(180, 120, 20, 0.1),
              transparent 45%
            ),
            radial-gradient(
              ellipse at 85% 5%,
              rgba(100, 70, 10, 0.08),
              transparent 40%
            ),
            var(--bg-base);
          font-family: "Inter", "Helvetica Neue", Arial, sans-serif;
          color: var(--text-primary);
        }

        /* ── Cards ── */
        .glass {
          background: var(--bg-card);
          border: 1px solid var(--border);
          box-shadow: 0 1px 3px rgba(0, 0, 0, 0.4), 0 0 0 0 transparent;
          backdrop-filter: blur(16px);
          transition: border-color 0.2s, box-shadow 0.2s;
        }

        .glass:hover {
          border-color: var(--border-accent);
          box-shadow: 0 1px 3px rgba(0, 0, 0, 0.4), 0 0 20px var(--glow);
        }

        /* ── Primary button (was purple-btn) ── */
        .purple-btn {
          background: var(--accent);
          border: none;
          color: #0d1117;
          font-weight: 600;
          letter-spacing: 0.01em;
          transition: background 0.2s, transform 0.1s;
        }

        .purple-btn:hover {
          background: var(--accent-dark);
          color: #0d1117;
          transform: translateY(-1px);
        }

        .purple-btn:active {
          transform: translateY(0);
        }

        .purple-btn:disabled {
          opacity: 0.45;
          transform: none;
        }

        /* ── Terminal / typing box ── */
        .terminal-box {
          border: 1px solid var(--border-accent);
          background: rgba(13, 17, 23, 0.9);
          box-shadow: inset 0 1px 0 rgba(217, 160, 50, 0.06);
        }

        .typing {
          color: var(--accent);
          min-height: 42px;
          font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
          font-size: 1.1rem;
        }

        .cursor {
          animation: blink 0.9s infinite;
        }

        @keyframes blink {
          50% { opacity: 0; }
        }

        /* ── Outline / ghost button (was contact-btn) ── */
        .contact-btn {
          border: 1px solid var(--border-accent);
          color: var(--accent);
          background: transparent;
          font-weight: 500;
          transition: background 0.2s, color 0.2s;
        }

        .contact-btn:hover {
          background: var(--accent-dim);
          color: var(--accent);
          border-color: var(--accent);
        }

        /* ── Form controls ── */
        .form-control {
          background: rgba(13, 17, 23, 0.8) !important;
          border-color: var(--border) !important;
          color: var(--text-primary) !important;
          transition: border-color 0.2s, box-shadow 0.2s;
        }

        .form-control:focus {
          border-color: var(--accent) !important;
          box-shadow: 0 0 0 3px rgba(217, 160, 50, 0.15) !important;
          outline: none;
        }

        .form-control::placeholder {
          color: var(--text-muted) !important;
        }

        /* ── Headings / accent text ── */
        .accent-text {
          color: var(--accent);
        }

        h5.section-title {
          color: var(--text-heading);
          font-weight: 600;
          letter-spacing: -0.01em;
        }

        /* ── List group (sources) ── */
        .list-group-item {
          background: rgba(13, 17, 23, 0.7) !important;
          border-color: var(--border) !important;
          color: var(--text-primary) !important;
          transition: background 0.15s;
        }

        .list-group-item:hover {
          background: var(--accent-dim) !important;
        }

        /* ── Table ── */
        .table-dark {
          --bs-table-bg: transparent;
          --bs-table-hover-bg: rgba(20, 184, 166, 0.06);
          --bs-table-border-color: var(--border);
        }

        .table th {
          color: var(--text-muted);
          font-size: 0.75rem;
          font-weight: 600;
          text-transform: uppercase;
          letter-spacing: 0.08em;
        }

        /* ── Badge overrides ── */
        .badge-accent {
          background: var(--accent-dim);
          color: var(--accent);
          border: 1px solid var(--border-accent);
          font-weight: 500;
        }

        /* ── FAQ marquee ── */
        .faq-marquee {
          overflow: hidden;
          white-space: nowrap;
          border: 1px solid var(--border);
          background: rgba(13, 17, 23, 0.6);
          border-radius: 8px;
        }

        .faq-track {
          display: inline-flex;
          gap: 12px;
          animation: scrollFaq 80s linear infinite;
        }

        .faq-card {
          display: inline-flex;
          align-items: center;
          gap: 10px;
          padding: 10px 16px;
          border-radius: 6px;
          background: var(--bg-card);
          border: 1px solid var(--border);
          min-width: max-content;
          color: var(--text-primary);
          font-size: 0.875rem;
        }

        .faq-count {
          color: var(--accent);
          font-size: 0.75rem;
          font-weight: 600;
        }

        @keyframes scrollFaq {
          from { transform: translateX(0); }
          to   { transform: translateX(-50%); }
        }

        /* ── Nav ── */
        .nav-brand {
          font-weight: 700;
          font-size: 1.1rem;
          color: var(--text-heading);
          letter-spacing: -0.02em;
        }

        .nav-brand span {
          color: var(--accent);
        }

        /* ── Divider dot in hero badge ── */
        .hero-badge {
          background: var(--accent-dim);
          border: 1px solid var(--border-accent);
          color: var(--accent);
          font-size: 0.7rem;
          font-weight: 600;
          letter-spacing: 0.1em;
        }
      `}</style>

      <div className="container py-5">
        {/* ── Navbar ── */}
        <nav className="d-flex justify-content-between align-items-center mb-5">
          <div className="nav-brand">
            Trust<span>Guard</span> AI
          </div>
          <a
            href="mailto:m.haseeb311@gmail.com"
            className="btn contact-btn rounded-2 px-4"
          >
            Contact Us
          </a>
        </nav>

        {/* ── Hero ── */}
        <section className="mb-5">
          <span className="badge rounded-2 px-3 py-2 mb-4 hero-badge">
            ● AI GOVERNANCE PLATFORM
          </span>

          <h1 className="display-3 fw-bold mb-4" style={{ color: "#f1f5f9", letterSpacing: "-0.02em" }}>
            Engineering trust <br />
            in every <span className="accent-text">AI response.</span>
          </h1>

          <p className="fs-5 mb-4" style={{ maxWidth: "780px", color: "#94a3b8" }}>
            TrustGuard AI helps teams detect hallucinations, verify sources,
            score AI risk, and create audit-ready governance workflows.
          </p>

          <div className="terminal-box rounded-4 p-4 mb-4">
            <div className="d-flex align-items-center gap-3">
              <span className="text-secondary">›</span>
              <span className="typing fs-4">
                {typedText}
                <span className="cursor text-light">|</span>
              </span>
            </div>
          </div>
        </section>

        {/* ── Feature cards ── */}
        <div className="row g-4 mb-5 text-center">
          {FEATURE_CARDS.map(([icon, title, description], index) => (
            <div className="col-md-3" key={index}>
              <div className="glass rounded-3 p-4 h-100">
                <div className="fs-2 mb-2 accent-text">{icon}</div>
                <h5 style={{ color: "#e2e8f0", fontWeight: 600 }}>{title}</h5>
                <p className="small mb-0" style={{ color: "#64748b" }}>{description}</p>
              </div>
            </div>
          ))}
        </div>

        {/* ── Main panel ── */}
        <div className="row g-4">
          {/* Left column */}
          <div className="col-lg-5">
            {/* Ingest URL */}
            <div className="glass rounded-3 p-4 mb-4">
              <h5 className="mb-3 section-title">◉ Add Knowledge Source</h5>

              <input
                value={url}
                onChange={(e) => setUrl(e.target.value)}
                className="form-control mb-3"
                placeholder="https://example.gov/policy"
              />

              <button
                onClick={ingestUrl}
                disabled={ingesting || !url}
                className="btn purple-btn w-100"
              >
                {ingesting ? "Ingesting..." : "Ingest URL"}
              </button>

              <button onClick={resetUrl} className="btn contact-btn w-100 mt-3">
                Clear URL
              </button>

              {ingestResult && (
                <div className="alert alert-success mt-3 mb-0 small">
                  {ingestResult.status} — {ingestResult.chunks_added || 0} chunks added
                </div>
              )}
            </div>

            {/* Ask a question */}
            <div className="glass rounded-3 p-4">
              <h5 className="mb-3 section-title">▣ Ask a Question</h5>

              <textarea
                value={question}
                onChange={(e) => setQuestion(e.target.value)}
                className="form-control mb-3"
                rows={7}
                placeholder="Ask a governance, policy, or compliance question..."
              />

              <button
                onClick={analyzeQuestion}
                disabled={loading || !question}
                className="btn purple-btn w-100 btn-lg"
              >
                {loading ? "Analyzing..." : "Analyze Query"}
              </button>

              <button onClick={resetQuery} className="btn contact-btn w-100 mt-3">
                Clear Query
              </button>
            </div>
          </div>

          {/* Right column */}
          <div className="col-lg-7">
            {/* Empty state */}
            {!result && (
              <div className="glass rounded-3 p-5 text-center h-100 d-flex flex-column align-items-center justify-content-center">
                <div className="accent-text mb-3" style={{ fontSize: "2rem" }}>◎</div>
                <h3 style={{ color: "#e2e8f0" }}>Ready for analysis</h3>
                <p style={{ color: "#64748b" }}>
                  Ask a question to generate a grounded answer, hallucination
                  score, risk level, and retrieved sources.
                </p>
              </div>
            )}

            {/* Results */}
            {result && (
              <div className="d-flex flex-column gap-4">
                {/* Answer */}
                <div className="glass rounded-3 p-4">
                  <div className="d-flex justify-content-between align-items-center mb-3">
                    <h5 className="section-title mb-0">›_ AI Answer</h5>
                    <span className={`badge text-bg-${riskBadge}`}>
                      {riskLevel} Risk
                    </span>
                  </div>
                  <p className="fs-5 lh-lg mb-0" style={{ color: "#cbd5e1" }}>{result.answer}</p>
                </div>

                {/* Hallucination + Risk */}
                <div className="row g-4">
                  <div className="col-md-6">
                    <div className="glass rounded-3 p-4 h-100">
                      <h5 className="section-title">Hallucination Analysis</h5>
                      <p>
                        <strong>Score:</strong>{" "}
                        <span className="accent-text fw-semibold">{hallucination?.hallucination_score}</span>
                      </p>
                      <p className="small mb-0" style={{ color: "#64748b" }}>
                        {hallucination?.reason}
                      </p>
                    </div>
                  </div>

                  <div className="col-md-6">
                    <div className="glass rounded-3 p-4 h-100">
                      <h5 className="section-title">Risk Analysis</h5>
                      <p>
                        <strong>Level:</strong>{" "}
                        <span className={`badge text-bg-${riskBadge} ms-1`}>{riskLevel}</span>
                      </p>
                      <p>
                        <strong>Status:</strong>{" "}
                        {result.risk_analysis.risk_status}
                      </p>
                      <p className="small mb-0" style={{ color: "#64748b" }}>
                        {result.risk_analysis.risk_reason}
                      </p>
                    </div>
                  </div>
                </div>

                {/* Feedback */}
                <div className="glass rounded-3 p-4">
                  <h5 className="mb-3 section-title">Was this answer useful?</h5>

                  <div className="d-flex gap-3 flex-wrap">
                    <button className="btn btn-success btn-sm px-3" onClick={() => submitFeedback("Correct")}>
                      ✓ Correct
                    </button>
                    <button className="btn btn-warning btn-sm px-3" onClick={() => submitFeedback("Partially Correct")}>
                      ~ Partially Correct
                    </button>
                    <button className="btn btn-danger btn-sm px-3" onClick={() => submitFeedback("Incorrect")}>
                      ✕ Incorrect
                    </button>
                  </div>

                  {feedbackStatus && (
                    <p className="accent-text mt-3 mb-0 small">{feedbackStatus}</p>
                  )}
                </div>

                {/* Sources */}
                <div className="glass rounded-3 p-4">
                  <h5 className="mb-3 section-title">Retrieved Sources</h5>

                  <div className="list-group">
                    {result.sources?.map((source: any, index: number) => (
                      <a
                        key={index}
                        href={source.url}
                        target="_blank"
                        className="list-group-item list-group-item-action"
                      >
                        <div className="small fw-medium">
                          {index + 1}. {source.title || "No Title"}
                        </div>
                        <small className="accent-text">{source.url}</small>
                      </a>
                    ))}
                  </div>
                </div>
              </div>
            )}
          </div>
        </div>

        {/* ── FAQ marquee ── */}
        {topQuestions.length > 0 && (
          <div className="glass rounded-3 p-4 mt-5">
            <h5 className="mb-3 section-title">Frequently Asked Questions</h5>

            <div className="faq-marquee rounded-2 p-3">
              <div className="faq-track">
                {[...topQuestions, ...topQuestions].map(
                  (item: any, index: number) => (
                    <div key={index} className="faq-card">
                      <span>{item.question}</span>
                      <span className="faq-count">Asked {item.count}×</span>
                    </div>
                  ),
                )}
              </div>
            </div>
          </div>
        )}

        {/* ── Audit log dashboard ── */}
        <div className="glass rounded-3 p-4 mt-5">
          <div className="d-flex justify-content-between align-items-center mb-3">
            <h5 className="section-title mb-0">Audit Log Dashboard</h5>

            <div className="d-flex gap-2">
              <button onClick={loadAuditLogs} className="btn purple-btn btn-sm px-3">
                {auditLoading ? "Loading..." : "Load Audit Logs"}
              </button>
              <button onClick={closeAuditLogs} className="btn contact-btn btn-sm px-3">
                Close
              </button>
            </div>
          </div>

          {auditLogs.length === 0 && (
            <p className="mb-0 small" style={{ color: "#64748b" }}>No audit logs loaded yet.</p>
          )}

          {auditLogs.length > 0 && (
            <>
              <div className="table-responsive">
                <table className="table table-dark table-hover align-middle">
                  <thead>
                    <tr>
                      <th>Time</th>
                      <th>Question</th>
                      <th>Risk Level</th>
                      <th>Risk Reason</th>
                    </tr>
                  </thead>
                  <tbody>
                    {paginatedAuditLogs.map((log: any, index: number) => (
                      <tr key={index}>
                        <td className="small">{log.timestamp}</td>
                        <td>{log.query}</td>
                        <td>
                          <span className="badge text-bg-info">
                            {log.risk_level}
                          </span>
                        </td>
                        <td className="small text-secondary">
                          {log.risk_reason}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>

              <div className="d-flex justify-content-between align-items-center mt-4">
                <button
                  className="btn btn-sm contact-btn"
                  disabled={auditPage === 1}
                  onClick={() => setAuditPage(auditPage - 1)}
                >
                  Previous
                </button>

                <span className="text-secondary">
                  Page {auditPage} of {totalAuditPages || 1}
                </span>

                <button
                  className="btn btn-sm contact-btn"
                  disabled={auditPage >= totalAuditPages}
                  onClick={() => setAuditPage(auditPage + 1)}
                >
                  Next
                </button>
              </div>
            </>
          )}
        </div>
      </div>
    </main>
  );
}
