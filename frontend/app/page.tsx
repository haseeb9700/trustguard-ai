"use client";

import { useEffect, useState } from "react";

const phrases = [
  "Detect hallucinations.",
  "Verify trusted sources.",
  "Score AI risk.",
  "Build trust in enterprise LLM systems.",
];

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

  const logsPerPage = 5;

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

  const analyzeQuestion = async () => {
    setLoading(true);
    setResult(null);
    setFeedbackStatus("");

    try {
      const response = await fetch(
        "https://trustguard-ai-production.up.railway.app/analyze",
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ question }),
        },
      );

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
      const response = await fetch(
        "https://trustguard-ai-production.up.railway.app/ingest-url",
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ url }),
        },
      );

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
      const response = await fetch(
        "https://trustguard-ai-production.up.railway.app/feedback",
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            question: result.question,
            answer: result.answer,
            feedback,
            corrected_answer: "",
          }),
        },
      );

      if (!response.ok) throw new Error("Feedback API error");

      setFeedbackStatus(`Feedback saved: ${feedback}`);
    } catch {
      alert("Could not save feedback.");
    }
  };

  const loadAuditLogs = async () => {
    setAuditLoading(true);

    try {
      const response = await fetch(
        "https://trustguard-ai-production.up.railway.app/audit-logs",
      );

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

  const hallucination = result?.hallucination_analysis || null;

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

  const totalAuditPages = Math.ceil(sortedAuditLogs.length / logsPerPage);

  const paginatedAuditLogs = sortedAuditLogs.slice(
    (auditPage - 1) * logsPerPage,
    auditPage * logsPerPage,
  );

  return (
    <main className="min-vh-100 text-light app-bg">
      <style jsx>{`
        .app-bg {
          background:
            radial-gradient(
              circle at top left,
              rgba(139, 92, 246, 0.28),
              transparent 35%
            ),
            radial-gradient(
              circle at top right,
              rgba(168, 85, 247, 0.18),
              transparent 35%
            ),
            #020204;
          font-family:
            ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
        }

        .glass {
          background: rgba(22, 18, 32, 0.78);
          border: 1px solid rgba(168, 85, 247, 0.35);
          box-shadow: 0 0 35px rgba(124, 58, 237, 0.18);
          backdrop-filter: blur(18px);
        }

        .purple-btn {
          background: linear-gradient(90deg, #7c3aed, #a855f7);
          border: none;
          color: white;
        }

        .purple-btn:hover {
          background: linear-gradient(90deg, #6d28d9, #9333ea);
          color: white;
        }

        .terminal-box {
          border: 1px solid rgba(168, 85, 247, 0.7);
          background: rgba(8, 6, 14, 0.85);
          box-shadow: 0 0 40px rgba(168, 85, 247, 0.22);
        }

        .typing {
          color: #c084fc;
          min-height: 42px;
        }

        .cursor {
          animation: blink 0.8s infinite;
        }

        @keyframes blink {
          50% {
            opacity: 0;
          }
        }

        .contact-btn {
          border: 1px solid rgba(216, 180, 254, 0.7);
          color: #d8b4fe;
          background: transparent;
        }

        .contact-btn:hover {
          background: #a855f7;
          color: white;
        }
        .faq-marquee {
          overflow: hidden;
          white-space: nowrap;
          border: 1px solid rgba(168, 85, 247, 0.35);
          background: rgba(8, 6, 14, 0.85);
        }

        .faq-track {
          display: inline-flex;
          gap: 18px;
          animation: scrollFaq 35s linear infinite;
        }

        .faq-card {
          display: inline-flex;
          align-items: center;
          gap: 12px;

          padding: 12px 18px;

          border-radius: 999px;

          background: rgba(22, 18, 32, 0.95);

          border: 1px solid rgba(216, 180, 254, 0.35);

          min-width: max-content;

          color: #e9d5ff;
        }

        .faq-count {
          color: #c084fc;
          font-size: 13px;
        }

        @keyframes scrollFaq {
          from {
            transform: translateX(0);
          }

          to {
            transform: translateX(-50%);
          }
        }
      `}</style>

      <div className="container py-5">
        <nav className="d-flex justify-content-between align-items-center mb-5">
          <div className="fw-bold fs-4">TrustGuard AI</div>

          <a
            href="mailto:m.haseeb311@gmail.com"
            className="btn contact-btn rounded-pill px-4"
          >
            Contact Us
          </a>
        </nav>

        <section className="mb-5">
          <span className="badge rounded-pill px-3 py-2 mb-4 glass text-light">
            ● AI GOVERNANCE PLATFORM
          </span>

          <h1 className="display-3 fw-bold mb-4">
            Engineering trust <br />
            in every <span style={{ color: "#a855f7" }}>AI response.</span>
          </h1>

          <p className="fs-5 text-secondary mb-4" style={{ maxWidth: "780px" }}>
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

        <div className="row g-4 mb-5 text-center">
          {[
            ["◎", "Detect", "Identify hallucinations in LLM responses"],
            ["盾", "Verify", "Trace answers to trusted sources"],
            ["⌁", "Score", "Assess risk levels automatically"],
            ["🔒", "Learn", "Collect feedback for future improvement"],
          ].map((item, index) => (
            <div className="col-md-3" key={index}>
              <div className="glass rounded-4 p-4 h-100">
                <div className="fs-2 mb-2" style={{ color: "#c084fc" }}>
                  {item[0]}
                </div>
                <h5 style={{ color: "#d8b4fe" }}>{item[1]}</h5>
                <p className="text-secondary small mb-0">{item[2]}</p>
              </div>
            </div>
          ))}
        </div>

        <div className="row g-4">
          <div className="col-lg-5">
            <div className="glass rounded-4 p-4 mb-4">
              <h5 className="mb-3" style={{ color: "#d8b4fe" }}>
                ◉ Add Knowledge Source
              </h5>

              <input
                value={url}
                onChange={(e) => setUrl(e.target.value)}
                className="form-control bg-black text-light border-secondary mb-3"
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
                <div className="alert alert-success mt-3 mb-0">
                  {ingestResult.status} — {ingestResult.chunks_added || 0}{" "}
                  chunks added
                </div>
              )}
            </div>

            <div className="glass rounded-4 p-4">
              <h5 className="mb-3" style={{ color: "#d8b4fe" }}>
                ▣ Ask a Question
              </h5>

              <textarea
                value={question}
                onChange={(e) => setQuestion(e.target.value)}
                className="form-control bg-black text-light border-secondary mb-3"
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

              <button
                onClick={resetQuery}
                className="btn contact-btn w-100 mt-3"
              >
                Clear Query
              </button>
            </div>
          </div>

          <div className="col-lg-7">
            {!result && (
              <div className="glass rounded-4 p-5 text-center h-100">
                <h3>Ready for analysis</h3>
                <p className="text-secondary">
                  Ask a question to generate a grounded answer, hallucination
                  score, risk level, and retrieved sources.
                </p>
              </div>
            )}

            {result && (
              <div className="d-flex flex-column gap-4">
                <div className="glass rounded-4 p-4">
                  <div className="d-flex justify-content-between align-items-center mb-3">
                    <h5 style={{ color: "#d8b4fe" }}>›_ AI Answer</h5>
                    <span className={`badge text-bg-${riskBadge}`}>
                      {riskLevel} Risk
                    </span>
                  </div>

                  <p className="fs-5 lh-lg mb-0">{result.answer}</p>
                </div>

                <div className="row g-4">
                  <div className="col-md-6">
                    <div className="glass rounded-4 p-4 h-100">
                      <h5 style={{ color: "#c084fc" }}>
                        Hallucination Analysis
                      </h5>
                      <p>
                        <strong>Score:</strong>{" "}
                        {hallucination?.hallucination_score}
                      </p>
                      <p className="text-secondary mb-0">
                        {hallucination?.reason}
                      </p>
                    </div>
                  </div>

                  <div className="col-md-6">
                    <div className="glass rounded-4 p-4 h-100">
                      <h5 style={{ color: "#c084fc" }}>Risk Analysis</h5>
                      <p>
                        <strong>Level:</strong>{" "}
                        <span className={`badge text-bg-${riskBadge}`}>
                          {riskLevel}
                        </span>
                      </p>
                      <p>
                        <strong>Status:</strong>{" "}
                        {result.risk_analysis.risk_status}
                      </p>
                      <p className="text-secondary mb-0">
                        {result.risk_analysis.risk_reason}
                      </p>
                    </div>
                  </div>
                </div>

                <div className="glass rounded-4 p-4">
                  <h5 className="mb-3" style={{ color: "#d8b4fe" }}>
                    Was this answer useful?
                  </h5>

                  <div className="d-flex gap-3 flex-wrap">
                    <button
                      className="btn btn-success"
                      onClick={() => submitFeedback("Correct")}
                    >
                      Correct
                    </button>

                    <button
                      className="btn btn-warning"
                      onClick={() => submitFeedback("Partially Correct")}
                    >
                      Partially Correct
                    </button>

                    <button
                      className="btn btn-danger"
                      onClick={() => submitFeedback("Incorrect")}
                    >
                      Incorrect
                    </button>
                  </div>

                  {feedbackStatus && (
                    <p className="text-success mt-3 mb-0">{feedbackStatus}</p>
                  )}
                </div>

                <div className="glass rounded-4 p-4">
                  <h5 className="mb-3" style={{ color: "#d8b4fe" }}>
                    Retrieved Sources
                  </h5>

                  <div className="list-group">
                    {result.sources?.map((source: any, index: number) => (
                      <a
                        key={index}
                        href={source.url}
                        target="_blank"
                        className="list-group-item list-group-item-action bg-black text-light border-secondary"
                      >
                        <div>
                          {index + 1}. {source.title || "No Title"}
                        </div>
                        <small style={{ color: "#c084fc" }}>{source.url}</small>
                      </a>
                    ))}
                  </div>
                </div>
              </div>
            )}
          </div>
        </div>

        {topQuestions.length > 0 && (
          <div className="glass rounded-4 p-4 mt-5">
            <h5
              className="mb-3"
              style={{
                color: "#d8b4fe",
              }}
            >
              Frequently Asked Questions
            </h5>

            <div
              className="
faq-marquee
rounded-4
p-3
"
            >
              <div
                className="
faq-track
"
              >
                {[...topQuestions, ...topQuestions].map(
                  (item: any, index: number) => (
                    <div
                      key={index}
                      className="
faq-card
"
                    >
                      <span>{item.question}</span>

                      <span
                        className="
faq-count
"
                      >
                        Asked
                        {item.count}×
                      </span>
                    </div>
                  ),
                )}
              </div>
            </div>
          </div>
        )}

        <div className="glass rounded-4 p-4 mt-5">
          <div className="d-flex justify-content-between align-items-center mb-3">
            <h5 style={{ color: "#d8b4fe" }}>Audit Log Dashboard</h5>

            <div className="d-flex gap-2">
              <button onClick={loadAuditLogs} className="btn purple-btn">
                {auditLoading ? "Loading..." : "Load Audit Logs"}
              </button>

              <button onClick={closeAuditLogs} className="btn contact-btn">
                Close
              </button>
            </div>
          </div>

          {auditLogs.length === 0 && (
            <p className="text-secondary mb-0">No audit logs loaded yet.</p>
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
