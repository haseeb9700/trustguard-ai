"use client";

import { useEffect, useState } from "react";

const phrases = [
  "Detect hallucinations.",
  "Verify trusted sources.",
  "Score AI risk.",
  "Build trust in enterprise LLM systems.",
];

const API_BASE = "https://trustguard-ai-production.up.railway.app";

const PRODUCT_CARDS = [
  { title: "Detect", desc: "Identify hallucinations in LLM responses", bg: "linear-gradient(135deg, #ff5530 0%, #ff7a45 100%)", badge: "Core" },
  { title: "Verify", desc: "Trace answers to trusted sources", bg: "linear-gradient(135deg, #ea5ec1 0%, #a855f7 100%)", badge: null },
  { title: "Score", desc: "Assess risk levels automatically", bg: "linear-gradient(135deg, #1456f0 0%, #3daeff 100%)", badge: null },
  { title: "Learn", desc: "Collect feedback for future improvement", bg: "linear-gradient(135deg, #a855f7 0%, #6d28d9 100%)", badge: null },
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
  const [analyzeError, setAnalyzeError] = useState("");
  const [ingestError, setIngestError] = useState("");
  const [auditError, setAuditError] = useState("");
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
    setAnalyzeError("");
    setActiveTab("sources");
    try {
      const res = await fetch(`${API_BASE}/analyze`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question }),
      });
      if (!res.ok) throw new Error();
      setResult(await res.json());
    } catch {
      setAnalyzeError("The analysis service is currently unreachable. Please try again in a moment.");
    }
    setLoading(false);
  };

  const ingestUrl = async () => {
    setIngesting(true);
    setIngestResult(null);
    setIngestError("");
    try {
      const res = await fetch(`${API_BASE}/ingest-url`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ url }),
      });
      if (!res.ok) throw new Error();
      setIngestResult(await res.json());
    } catch {
      setIngestError("Could not ingest this URL. Verify it is publicly accessible and try again.");
    }
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
    } catch {
      setFeedbackStatus("Could not save feedback. Please try again.");
    }
  };

  const loadAuditLogs = async () => {
    setAuditLoading(true);
    setAuditError("");
    try {
      const res = await fetch(`${API_BASE}/audit-logs`);
      if (!res.ok) throw new Error();
      const data = await res.json();
      setAuditLogs(data.logs || []);
      setTopQuestions(data.top_questions || []);
      setAuditPage(1);
    } catch {
      setAuditError("Could not load audit logs. Please try again.");
    }
    setAuditLoading(false);
  };

  const resetQuery = () => { setQuestion(""); setResult(null); setFeedbackStatus(""); setAnalyzeError(""); };
  const resetUrl = () => { setUrl(""); setIngestResult(null); setIngestError(""); };
  const closeAuditLogs = () => { setAuditLogs([]); setTopQuestions([]); setAuditPage(1); };

  const hallucination = result?.hallucination_analysis ?? null;
  const riskLevel = result?.risk_analysis?.risk_level;
  const riskStyles: Record<string, { color: string; bg: string; border: string }> = {
    Low:    { color: "#1ba673", bg: "#e8ffea", border: "#b5e8c4" },
    Medium: { color: "#d97706", bg: "#fffbeb", border: "#fcd34d" },
    High:   { color: "#dc2626", bg: "#fef2f2", border: "#fca5a5" },
  };
  const rs = riskStyles[riskLevel] ?? riskStyles["Low"];

  const sorted = [...auditLogs].sort((a, b) => new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime());
  const totalPages = Math.ceil(sorted.length / LOGS_PER_PAGE);
  const paginated = sorted.slice((auditPage - 1) * LOGS_PER_PAGE, auditPage * LOGS_PER_PAGE);

  return (
    <main style={{ minHeight: "100vh", background: "#ffffff", fontFamily: "var(--font-dm-sans), 'DM Sans', Inter, ui-sans-serif, system-ui, sans-serif", color: "#0a0a0a" }}>
      <style jsx>{`
        * { box-sizing: border-box; }

        .promo-banner {
          background: #0a0a0a;
          color: #ffffff;
          font-size: 13px;
          font-weight: 500;
          text-align: center;
          padding: 10px 20px;
          letter-spacing: 0.01em;
        }
        .promo-banner span { color: #a8aab2; }

        .card {
          background: #ffffff;
          border: 1px solid #e5e7eb;
          border-radius: 16px;
          padding: 24px;
        }
        .card-accent {
          background: #ffffff;
          border: 1px solid #e5e7eb;
          border-radius: 16px;
          padding: 24px;
          box-shadow: rgba(0, 0, 0, 0.08) 0px 4px 6px 0px;
        }

        .lbl {
          font-size: 13px;
          font-weight: 600;
          letter-spacing: .02em;
          text-transform: uppercase;
          color: #5f5f5f;
          margin-bottom: 12px;
        }

        input, textarea {
          width: 100%;
          padding: 10px 16px;
          border: 1px solid #e5e7eb;
          border-radius: 8px;
          font-size: 14px;
          background: #ffffff;
          color: #0a0a0a;
          outline: none;
          font-family: inherit;
          margin-bottom: 10px;
          transition: border-color .18s, box-shadow .18s;
        }
        input::placeholder, textarea::placeholder { color: #a8aab2; }
        input:focus, textarea:focus {
          border-color: #1d4ed8;
          box-shadow: 0 0 0 1px #1d4ed8;
        }

        .btn-primary {
          background: #0a0a0a;
          color: #ffffff;
          border: none;
          border-radius: 9999px;
          padding: 11px 24px;
          font-size: 14px;
          font-weight: 600;
          cursor: pointer;
          width: 100%;
          margin-bottom: 8px;
          font-family: inherit;
          transition: background .18s;
        }
        .btn-primary:hover:not(:disabled) { background: #222222; }
        .btn-primary:disabled { background: #e5e7eb; color: #a8aab2; cursor: not-allowed; }

        .btn-ghost {
          background: transparent;
          color: #0a0a0a;
          border: 1px solid #e5e7eb;
          border-radius: 9999px;
          padding: 11px 24px;
          font-size: 14px;
          font-weight: 600;
          cursor: pointer;
          width: 100%;
          font-family: inherit;
          transition: border-color .18s, background .18s;
        }
        .btn-ghost:hover:not(:disabled) { border-color: #0a0a0a; background: #f7f8fa; }
        .btn-ghost:disabled { opacity: .35; cursor: not-allowed; }

        .btn-sm { padding: 8px 18px; font-size: 13px; width: auto; margin-bottom: 0; }

        .nav {
          display: flex;
          justify-content: space-between;
          align-items: center;
          padding: 16px 0;
          border-bottom: 1px solid #eaecf0;
        }
        .logo { font-weight: 700; font-size: 18px; letter-spacing: -.02em; color: #0a0a0a; }
        .nav-contact {
          background: #0a0a0a;
          color: #ffffff;
          border-radius: 9999px;
          padding: 9px 22px;
          font-size: 14px;
          font-weight: 600;
          cursor: pointer;
          text-decoration: none;
          transition: background .18s;
        }
        .nav-contact:hover { background: #222222; color: #ffffff; }

        .hero { padding: 96px 0 64px; text-align: left; }
        .hero h1 {
          font-size: clamp(40px, 7vw, 80px);
          font-weight: 600;
          letter-spacing: -2px;
          line-height: 1.10;
          margin: 0 0 20px;
          color: #0a0a0a;
        }
        .hero-sub {
          font-size: 18px;
          font-weight: 500;
          color: #5f5f5f;
          max-width: 560px;
          margin: 0 0 32px;
          line-height: 1.5;
        }

        .terminal {
          background: #f7f8fa;
          border: 1px solid #e5e7eb;
          border-radius: 12px;
          padding: 14px 20px;
          margin-bottom: 0;
          display: flex;
          align-items: center;
          gap: 12px;
          max-width: 560px;
        }
        .typing-text { font-size: 15px; font-family: ui-monospace, monospace; color: #0a0a0a; font-weight: 500; min-height: 24px; }
        .cursor { animation: blink .8s infinite; color: #0a0a0a; }
        @keyframes blink { 50% { opacity: 0; } }

        .section-title {
          font-size: 32px;
          font-weight: 600;
          letter-spacing: -0.5px;
          line-height: 1.25;
          color: #0a0a0a;
          margin: 0 0 8px;
        }
        .section-sub { font-size: 14px; color: #5f5f5f; margin: 0 0 28px; }

        .product-grid { display: grid; grid-template-columns: repeat(4,1fr); gap: 12px; margin-bottom: 64px; }
        @media (max-width: 1023px) { .product-grid { grid-template-columns: repeat(2,1fr); } }
        @media (max-width: 540px) { .product-grid { grid-template-columns: 1fr; } }

        .product-card {
          border-radius: 16px;
          padding: 18px 20px;
          min-height: 96px;
          color: #ffffff;
          display: flex;
          flex-direction: column;
          justify-content: flex-end;
          position: relative;
          overflow: hidden;
        }
        .product-title { font-size: 17px; font-weight: 600; letter-spacing: -.02em; line-height: 1.2; margin-bottom: 3px; }
        .product-desc { font-size: 13px; opacity: .85; line-height: 1.45; }
        .product-badge {
          position: absolute;
          top: 12px;
          right: 14px;
          background: rgba(255,255,255,.2);
          backdrop-filter: blur(4px);
          color: #ffffff;
          font-size: 11px;
          font-weight: 600;
          padding: 2px 10px;
          border-radius: 9999px;
        }

        .main-grid { display: grid; grid-template-columns: 340px 1fr; gap: 16px; margin-bottom: 80px; align-items: start; }
        @media (max-width: 860px) { .main-grid { grid-template-columns: 1fr; } }

        .risk-badge {
          display: inline-block;
          padding: 4px 12px;
          border-radius: 9999px;
          font-size: 13px;
          font-weight: 600;
          border: 1px solid;
        }

        .meta-row {
          display: grid;
          grid-template-columns: 1fr 1px 1fr;
          background: #f7f8fa;
          border: 1px solid #eaecf0;
          border-radius: 12px;
          margin-top: 16px;
          overflow: hidden;
        }
        .meta-col { padding: 14px 16px; }
        .meta-div { background: #eaecf0; }
        .meta-label { font-size: 13px; font-weight: 600; text-transform: uppercase; letter-spacing: .02em; color: #8e8e93; margin-bottom: 4px; }
        .meta-val { font-size: 16px; font-weight: 700; color: #0a0a0a; }
        .meta-sub { font-size: 13px; color: #5f5f5f; margin-top: 2px; line-height: 1.5; }

        .tabs { display: flex; gap: 0; margin-bottom: 16px; border-bottom: 1px solid #e5e7eb; }
        .tab {
          border: none;
          border-bottom: 2px solid transparent;
          background: transparent;
          padding: 12px 20px;
          font-size: 14px;
          font-weight: 600;
          cursor: pointer;
          color: #5f5f5f;
          font-family: inherit;
          transition: color .15s, border-color .15s;
        }
        .tab.active { color: #0a0a0a; border-bottom-color: #0a0a0a; }

        .source-item {
          display: flex;
          flex-direction: column;
          gap: 2px;
          padding: 12px 16px;
          border: 1px solid #e5e7eb;
          border-radius: 12px;
          background: #ffffff;
          text-decoration: none;
          transition: border-color .15s, background .15s;
          margin-bottom: 8px;
        }
        .source-item:last-child { margin-bottom: 0; }
        .source-item:hover { border-color: #0a0a0a; background: #f7f8fa; }
        .source-title { font-size: 14px; font-weight: 500; color: #222222; }
        .source-url { font-size: 13px; color: #1d4ed8; }

        .fb-btn {
          border: 1px solid #e5e7eb;
          background: #ffffff;
          border-radius: 9999px;
          padding: 9px 18px;
          font-size: 13px;
          font-weight: 600;
          cursor: pointer;
          color: #45515e;
          font-family: inherit;
          transition: .15s;
        }
        .fb-btn.correct:hover { background: #e8ffea; border-color: #1ba673; color: #1ba673; }
        .fb-btn.partial:hover { background: #fffbeb; border-color: #d97706; color: #d97706; }
        .fb-btn.wrong:hover   { background: #fef2f2; border-color: #dc2626; color: #dc2626; }

        .sec-title { font-size: 20px; font-weight: 600; letter-spacing: -.02em; color: #0a0a0a; margin-bottom: 12px; }

        .audit-table { width: 100%; border-collapse: collapse; border: 1px solid #e5e7eb; border-radius: 8px; overflow: hidden; }
        .audit-th {
          text-align: left;
          padding: 12px 16px;
          background: #f7f8fa;
          color: #5f5f5f;
          font-size: 13px;
          font-weight: 600;
          text-transform: uppercase;
          letter-spacing: .02em;
          border-bottom: 1px solid #e5e7eb;
        }
        .audit-td { padding: 14px 16px; color: #222222; font-size: 14px; border-bottom: 1px solid #eaecf0; vertical-align: top; }

        .faq-track { display: inline-flex; gap: 10px; animation: scrollFaq 80s linear infinite; }
        .faq-pill {
          display: inline-flex;
          align-items: center;
          gap: 10px;
          padding: 9px 18px;
          border-radius: 9999px;
          border: 1px solid #e5e7eb;
          background: #ffffff;
          font-size: 14px;
          color: #222222;
          white-space: nowrap;
        }
        .faq-count { color: #5f5f5f; font-size: 13px; font-weight: 600; }
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

        .footer {
          background: #0a0a0a;
          color: #ffffff;
          margin-top: 96px;
          padding: 64px 0;
        }
        .footer-inner { max-width: 1280px; margin: 0 auto; padding: 0 32px; }
        .footer-brand { font-size: 20px; font-weight: 700; letter-spacing: -.02em; margin-bottom: 6px; }
        .footer-tag { font-size: 14px; color: #a8aab2; margin-bottom: 32px; }
        .footer-row { display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 12px; border-top: 1px solid #222222; padding-top: 24px; }
        .footer-link { color: #a8aab2; font-size: 14px; text-decoration: none; }
        .footer-link:hover { color: #ffffff; }
        .footer-micro { font-size: 12px; color: #a8aab2; }
      `}</style>

      {/* Promo banner */}
      <div className="promo-banner">
        TrustGuard AI <span>— Audit-ready governance for enterprise LLM systems</span>
      </div>

      <div style={{ maxWidth: 1280, margin: "0 auto", padding: "0 32px" }}>

        {/* Nav */}
        <nav className="nav">
          <span className="logo">TrustGuard AI</span>
          <a href="mailto:m.haseeb311@gmail.com" className="nav-contact">Contact Us</a>
        </nav>

        {/* Hero */}
        <section className="hero">
          <h1>Engineering trust<br />in every AI response.</h1>
          <p className="hero-sub">
            Detect hallucinations, verify sources, score risk, and create audit-ready governance workflows for enterprise LLM systems.
          </p>
          <div className="terminal">
            <span style={{ color: "#5f5f5f", fontFamily: "monospace", fontSize: 15 }}>›</span>
            <span className="typing-text">
              {typedText}<span className="cursor">|</span>
            </span>
          </div>
        </section>

        {/* Product matrix */}
        <div className="product-grid">
          {PRODUCT_CARDS.map(({ title, desc, bg, badge }) => (
            <div className="product-card" style={{ background: bg }} key={title}>
              {badge && <span className="product-badge">{badge}</span>}
              <div className="product-title">{title}</div>
              <div className="product-desc">{desc}</div>
            </div>
          ))}
        </div>

        {/* Main panel */}
        <h2 className="section-title">Ask. Verify. Trust.</h2>
        <p className="section-sub">Feed it a trusted source, ask anything — get a grounded answer with risk scored and receipts attached.</p>
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
                ingestResult.status === "success" ? (
                  <div style={{ marginTop: 12, padding: "10px 16px", background: "#e8ffea", border: "1px solid #b5e8c4", borderRadius: 8, fontSize: 13, color: "#1ba673", fontWeight: 500 }}>
                    Source ingested successfully — {ingestResult.chunks_added || 0} chunks added
                  </div>
                ) : (
                  <div style={{ marginTop: 12, padding: "10px 16px", background: "#fffbeb", border: "1px solid #fcd34d", borderRadius: 8, fontSize: 13, color: "#d97706", fontWeight: 500 }}>
                    {ingestResult.message || "Ingestion did not complete."}
                  </div>
                )
              )}
              {ingestError && (
                <div style={{ marginTop: 12, padding: "10px 16px", background: "#fef2f2", border: "1px solid #fca5a5", borderRadius: 8, fontSize: 13, color: "#dc2626", fontWeight: 500 }}>
                  {ingestError}
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
            {analyzeError && (
              <div style={{ marginBottom: 14, padding: "12px 16px", background: "#fef2f2", border: "1px solid #fca5a5", borderRadius: 12, fontSize: 13, color: "#dc2626", fontWeight: 500 }}>
                {analyzeError}
              </div>
            )}
            {!result ? (
              <div className="card empty-state">
                <div style={{ fontSize: 28, color: "#a8aab2" }}>◎</div>
                <div style={{ fontWeight: 600, color: "#45515e", fontSize: 16 }}>Ready for analysis</div>
                <div style={{ fontSize: 14, color: "#8e8e93", maxWidth: 280, lineHeight: 1.6 }}>
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
                  <p style={{ fontSize: 16, lineHeight: 1.6, color: "#222222", margin: 0 }}>{result.answer}</p>
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
                            <span className="source-title">{i + 1}. {src.title || "Untitled Source"}</span>
                            <span className="source-url">{src.url}</span>
                          </a>
                        ))
                      ) : (
                        <p style={{ fontSize: 14, color: "#8e8e93", margin: 0 }}>No sources retrieved.</p>
                      )}
                    </div>
                  )}

                  {activeTab === "feedback" && (
                    <div>
                      <p className="sec-title" style={{ fontSize: 15 }}>Was this answer useful?</p>
                      <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
                        <button className="fb-btn correct" onClick={() => submitFeedback("Correct")}>✓ Correct</button>
                        <button className="fb-btn partial" onClick={() => submitFeedback("Partially Correct")}>~ Partially Correct</button>
                        <button className="fb-btn wrong" onClick={() => submitFeedback("Incorrect")}>✕ Incorrect</button>
                      </div>
                      {feedbackStatus && <p style={{ marginTop: 12, marginBottom: 0, fontSize: 14, color: "#0a0a0a", fontWeight: 500 }}>{feedbackStatus}</p>}
                    </div>
                  )}
                </div>

              </div>
            )}
          </div>
        </div>

        {/* FAQ marquee */}
        {topQuestions.length > 0 && (
          <div style={{ marginBottom: 48, overflow: "hidden" }}>
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
        <div style={{ marginBottom: 48 }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 16 }}>
            <div>
              <h2 className="section-title" style={{ marginBottom: 4 }}>Every answer, on the record.</h2>
              <p className="section-sub" style={{ marginBottom: 0 }}>Full traceability of every query, answer, and risk decision.</p>
            </div>
            <div style={{ display: "flex", gap: 8 }}>
              <button onClick={loadAuditLogs} className="btn-primary btn-sm">{auditLoading ? "Loading…" : "Load Logs"}</button>
              <button onClick={closeAuditLogs} className="btn-ghost btn-sm">Clear</button>
            </div>
          </div>

          {auditError && (
            <p style={{ color: "#dc2626", fontSize: 13, marginTop: 0, marginBottom: 10, fontWeight: 500 }}>{auditError}</p>
          )}
          {auditLogs.length === 0 ? (
            <div className="card" style={{ textAlign: "center", padding: 40 }}>
              <p style={{ color: "#8e8e93", fontSize: 14, margin: 0 }}>No audit logs loaded.</p>
            </div>
          ) : (
            <>
              <div style={{ overflowX: "auto" }}>
                <table className="audit-table">
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
                          <td className="audit-td" style={{ whiteSpace: "nowrap", color: "#8e8e93", fontSize: 13 }}>{log.timestamp}</td>
                          <td className="audit-td">{log.query}</td>
                          <td className="audit-td">
                            <span style={{ display: "inline-block", padding: "3px 12px", borderRadius: 9999, fontSize: 13, fontWeight: 600, color: s.color, background: s.bg, border: `1px solid ${s.border}` }}>
                              {log.risk_level}
                            </span>
                          </td>
                          <td className="audit-td" style={{ color: "#5f5f5f" }}>{log.risk_reason}</td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginTop: 14 }}>
                <button className="btn-ghost btn-sm" disabled={auditPage === 1} onClick={() => setAuditPage(auditPage - 1)}>← Previous</button>
                <span style={{ fontSize: 13, color: "#8e8e93" }}>Page {auditPage} of {totalPages || 1}</span>
                <button className="btn-ghost btn-sm" disabled={auditPage >= totalPages} onClick={() => setAuditPage(auditPage + 1)}>Next →</button>
              </div>
            </>
          )}
        </div>

      </div>

      {/* Footer */}
      <footer className="footer">
        <div className="footer-inner">
          <div className="footer-brand">TrustGuard AI</div>
          <div className="footer-tag">Trust with every response.</div>
          <div className="footer-row">
            <span className="footer-micro">© {new Date().getFullYear()} TrustGuard AI — Enterprise AI Governance Platform</span>
            <div style={{ display: "flex", gap: 20 }}>
              <a className="footer-link" href="mailto:m.haseeb311@gmail.com">Contact</a>
              <span className="footer-micro" style={{ alignSelf: "center" }}>Built with Next.js, FastAPI &amp; OpenAI</span>
            </div>
          </div>
        </div>
      </footer>
    </main>
  );
}
