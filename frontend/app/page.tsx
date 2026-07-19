"use client";

import { useEffect, useRef, useState } from "react";

const phrases = [
  "Detect hallucinations.",
  "Verify trusted sources.",
  "Score AI risk.",
  "Build trust in enterprise LLM systems.",
];

const API_BASE = process.env.NEXT_PUBLIC_API_BASE ?? "https://trustguard-ai-production.up.railway.app";

const PRODUCT_CARDS = [
  { title: "Detect", desc: "Identify hallucinations in LLM responses", bg: "linear-gradient(135deg, #ff5530 0%, #ff7a45 100%)", badge: "Core" },
  { title: "Verify", desc: "Trace answers to trusted sources", bg: "linear-gradient(135deg, #ea5ec1 0%, #a855f7 100%)", badge: null },
  { title: "Score", desc: "Assess risk levels automatically", bg: "linear-gradient(135deg, #1456f0 0%, #3daeff 100%)", badge: null },
  { title: "Learn", desc: "Collect feedback for future improvement", bg: "linear-gradient(135deg, #a855f7 0%, #6d28d9 100%)", badge: null },
];

const LOGS_PER_PAGE = 5;

const DEMO_SOURCE_URL = "https://en.wikipedia.org/wiki/General_Data_Protection_Regulation";

const PIPELINE_STAGES = [
  "Rewriting query",
  "Retrieving sources",
  "Generating answer",
  "Verifying claims",
  "Scoring risk",
  "Getting Guardian ready for follow-ups",
];

const HOW_IT_WORKS = [
  { step: "01", title: "Ingest a trusted source", desc: "Paste a URL — the content is scraped, chunked, and embedded as the only allowed evidence." },
  { step: "02", title: "Ask anything", desc: "Your question is rewritten, matched against the source, and answered strictly from it." },
  { step: "03", title: "Every claim verified", desc: "The answer is split into claims; each is checked against the source and labeled." },
  { step: "04", title: "Risk scored & logged", desc: "One contradicted claim flags the whole answer. Everything lands in the audit log." },
];

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
  const [stats, setStats] = useState<any>(null);
  const [trickQuestions, setTrickQuestions] = useState<string[]>([]);
  const [pipelineStage, setPipelineStage] = useState(0);
  const [knowledgeSources, setKnowledgeSources] = useState<any[]>([]);
  const [frontIdx, setFrontIdx] = useState(0);
  const cardRefs = useRef<(HTMLDivElement | null)[]>([]);

  // Admin mode gates knowledge-base edits (ingest/delete). The key comes from
  // a ?admin=<key> URL param (persisted to localStorage) so ordinary visitors
  // see a read-only, tamper-proof source list while the curator retains control.
  const [adminKey, setAdminKey] = useState("");
  const isAdmin = adminKey.length > 0;

  useEffect(() => {
    try {
      const fromUrl = new URLSearchParams(window.location.search).get("admin");
      if (fromUrl) localStorage.setItem("tg_admin_key", fromUrl);
      const key = fromUrl || localStorage.getItem("tg_admin_key") || "";
      if (key) setAdminKey(key);
    } catch {
      /* localStorage unavailable — stay in read-only mode */
    }
  }, []);

  const exitAdmin = () => {
    try {
      localStorage.removeItem("tg_admin_key");
    } catch {
      /* ignore */
    }
    setAdminKey("");
  };

  // Follow-up chat — appears only after a question is analyzed. Every follow-up
  // runs through /analyze, so answers stay grounded, verified, and risk-scored
  // rather than becoming free-form (and potentially hallucinated) chat.
  const [chatOpen, setChatOpen] = useState(false);
  const [chatInput, setChatInput] = useState("");
  const [chatLoading, setChatLoading] = useState(false);
  const [chatMessages, setChatMessages] = useState<any[]>([]);
  const chatBodyRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    if (result) {
      setChatMessages([
        { role: "user", text: result.question },
        {
          role: "assistant",
          text: result.answer,
          risk: result.risk_analysis?.risk_level,
          sources: result.sources ?? [],
        },
      ]);
    } else {
      setChatMessages([]);
      setChatOpen(false);
    }
  }, [result]);

  useEffect(() => {
    if (chatBodyRef.current) {
      chatBodyRef.current.scrollTop = chatBodyRef.current.scrollHeight;
    }
  }, [chatMessages, chatOpen, chatLoading]);

  const sendFollowUp = async () => {
    const q = chatInput.trim();
    if (!q || chatLoading) return;
    setChatMessages((m) => [...m, { role: "user", text: q }]);
    setChatInput("");
    setChatLoading(true);
    try {
      const res = await fetch(`${API_BASE}/analyze`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question: q }),
      });
      if (!res.ok) throw new Error();
      const data = await res.json();
      setChatMessages((m) => [
        ...m,
        {
          role: "assistant",
          text: data.answer,
          risk: data.risk_analysis?.risk_level,
          sources: data.sources ?? [],
        },
      ]);
    } catch {
      setChatMessages((m) => [
        ...m,
        {
          role: "assistant",
          text: "Sorry — I couldn't analyze that follow-up. Please try again.",
          error: true,
        },
      ]);
    } finally {
      setChatLoading(false);
    }
  };

  // Elliptical orbit: all cards ride one ellipse and rotate counter-clockwise.
  // A card grows and rises to the top layer as it swings toward the viewer
  // (front of the ellipse), then shrinks and fades as it recedes to the back.
  useEffect(() => {
    const N = PRODUCT_CARDS.length;
    const RX = 232;   // horizontal radius (px) — wider, more stretched ellipse
    const RY = 60;    // vertical radius (px) — flatter than wide = ellipse
    const SPEED = 0.00042; // radians per ms (counter-clockwise)

    const reduce =
      typeof window !== "undefined" &&
      window.matchMedia?.("(prefers-reduced-motion: reduce)").matches;

    const place = (i: number, theta: number) => {
      const el = cardRefs.current[i];
      if (!el) return 0;
      const x = RX * Math.cos(theta);
      const y = RY * Math.sin(theta);          // front (toward viewer) when y > 0
      const depth = (Math.sin(theta) + 1) / 2; // 0 = far back, 1 = closest
      const scale = 0.58 + depth * 0.56;       // 0.58 (small/away) .. 1.14 (big/near)
      el.style.transform =
        `translate(-50%, -50%) translate(${x.toFixed(1)}px, ${y.toFixed(1)}px) scale(${scale.toFixed(3)})`;
      el.style.opacity = (0.38 + depth * 0.62).toFixed(3);
      el.style.zIndex = String(Math.round(depth * 100));
      return y;
    };

    if (reduce) {
      // Static, readable fan for users who prefer reduced motion.
      PRODUCT_CARDS.forEach((_, i) => place(i, (i / N) * Math.PI * 2 - Math.PI / 2));
      return;
    }

    let raf = 0;
    const start = performance.now();
    let lastFront = -1;

    const frame = (now: number) => {
      const t = (now - start) * SPEED;
      let bestFront = 0;
      let bestY = -Infinity;
      for (let i = 0; i < N; i++) {
        // Subtracting t sweeps counter-clockwise; offset each card evenly.
        const theta = (i / N) * Math.PI * 2 - t;
        const y = place(i, theta);
        if (y > bestY) {
          bestY = y;
          bestFront = i;
        }
      }
      if (bestFront !== lastFront) {
        lastFront = bestFront;
        setFrontIdx(bestFront);
      }
      raf = requestAnimationFrame(frame);
    };

    raf = requestAnimationFrame(frame);
    return () => cancelAnimationFrame(raf);
  }, []);

  const loadSources = () => {
    fetch(`${API_BASE}/sources`)
      .then((res) => (res.ok ? res.json() : null))
      .then((data) => setKnowledgeSources(data?.sources ?? []))
      .catch(() => {});
  };

  useEffect(() => { loadSources(); }, []);

  const deleteKnowledgeSource = async (sourceUrl: string) => {
    try {
      const res = await fetch(`${API_BASE}/sources?url=${encodeURIComponent(sourceUrl)}`, {
        method: "DELETE",
        headers: adminKey ? { "X-API-Key": adminKey } : {},
      });
      if (!res.ok) throw new Error();
      loadSources();
    } catch {
      setIngestError("Could not delete this source (admin key may be required).");
    }
  };

  useEffect(() => {
    if (!loading) { setPipelineStage(0); return; }
    const timer = setInterval(() => {
      setPipelineStage((s) => Math.min(s + 1, PIPELINE_STAGES.length - 1));
    }, 3000);
    return () => clearInterval(timer);
  }, [loading]);

  useEffect(() => {
    fetch(`${API_BASE}/stats`)
      .then((res) => (res.ok ? res.json() : null))
      .then((data) => { if (data?.total_queries > 0) setStats(data); })
      .catch(() => {});
  }, []);

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

  const analyzeQuestion = async (overrideQuestion?: string) => {
    const q = overrideQuestion ?? question;
    if (overrideQuestion) setQuestion(overrideQuestion);
    setLoading(true);
    setResult(null);
    setFeedbackStatus("");
    setAnalyzeError("");
    setActiveTab("sources");
    try {
      const res = await fetch(`${API_BASE}/analyze`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question: q }),
      });
      if (!res.ok) throw new Error();
      setResult(await res.json());
    } catch {
      setAnalyzeError("The analysis service is currently unreachable. Please try again in a moment.");
    }
    setLoading(false);
  };

  const ingestUrl = async (overrideUrl?: string) => {
    const target = overrideUrl ?? url;
    if (overrideUrl) setUrl(overrideUrl);
    setIngesting(true);
    setIngestResult(null);
    setIngestError("");
    try {
      const res = await fetch(`${API_BASE}/ingest-url`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          ...(adminKey ? { "X-API-Key": adminKey } : {}),
        },
        body: JSON.stringify({ url: target }),
      });
      if (!res.ok) throw new Error();
      const data = await res.json();
      setIngestResult(data);
      if (data.status === "success") {
        if (Array.isArray(data.trick_questions)) setTrickQuestions(data.trick_questions);
        loadSources();
      }
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
  const resetUrl = () => { setUrl(""); setIngestResult(null); setIngestError(""); setTrickQuestions([]); };
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

        .orbit-stage {
          position: relative;
          height: 300px;
          margin-bottom: 56px;
        }

        .orbit-rail {
          position: absolute;
          left: 50%;
          top: 50%;
          transform: translate(-50%, -50%);
          width: 520px;
          height: 164px;
          max-width: 94%;
        }

        .orbit-card {
          position: absolute;
          left: 50%;
          top: 50%;
          border-radius: 9999px;
          padding: 20px 40px;
          color: #ffffff;
          text-align: center;
          width: 230px;
          overflow: hidden;
          box-shadow: rgba(0,0,0,.16) 0 16px 34px -10px;
          will-change: transform, opacity;
          /* transform / opacity / z-index are set every frame by the orbit loop */
          transform: translate(-50%, -50%);
        }

        .orbit-glow {
          position: absolute;
          inset: 0;
          background: radial-gradient(ellipse at 30% 18%, rgba(255,255,255,.4), transparent 58%);
          pointer-events: none;
        }

        .orbit-title { font-size: 24px; font-weight: 600; letter-spacing: -.02em; line-height: 1.15; margin-bottom: 3px; position: relative; }
        .orbit-desc { font-size: 13px; opacity: .9; line-height: 1.4; position: relative; }

        .orbit-dots { position: absolute; left: 0; right: 0; bottom: 0; display: flex; justify-content: center; gap: 8px; }
        .orbit-dot {
          width: 8px;
          height: 8px;
          border-radius: 9999px;
          border: none;
          background: #e5e7eb;
          cursor: pointer;
          padding: 0;
          transition: background .2s, transform .2s;
        }
        .orbit-dot.active { background: #0a0a0a; transform: scale(1.3); }

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

        .how-grid { display: grid; grid-template-columns: repeat(4,1fr); gap: 12px; margin-bottom: 64px; }
        @media (max-width: 1023px) { .how-grid { grid-template-columns: repeat(2,1fr); } }
        @media (max-width: 540px) { .how-grid { grid-template-columns: 1fr; } }
        .how-cell { border-top: 2px solid #0a0a0a; padding: 14px 4px 0; }
        .how-step { font-size: 12px; font-weight: 600; color: #a8aab2; margin-bottom: 6px; }
        .how-title { font-size: 15px; font-weight: 600; color: #0a0a0a; margin-bottom: 4px; letter-spacing: -.01em; }
        .how-desc { font-size: 13px; color: #5f5f5f; line-height: 1.5; }

        .trick-pill {
          text-align: left;
          background: #f7f8fa;
          border: 1px solid #e5e7eb;
          border-radius: 9999px;
          padding: 8px 16px;
          font-size: 13px;
          color: #45515e;
          cursor: pointer;
          font-family: inherit;
          transition: border-color .15s, background .15s;
        }
        .trick-pill:hover:not(:disabled) { border-color: #0a0a0a; background: #ffffff; }
        .trick-pill:disabled { opacity: .5; cursor: not-allowed; }

        .claim-row {
          display: flex;
          gap: 12px;
          align-items: flex-start;
          padding: 12px 14px;
          background: #ffffff;
          border: 1px solid #eaecf0;
          border-radius: 12px;
        }
        .claim-chip {
          flex-shrink: 0;
          display: inline-block;
          padding: 3px 10px;
          border-radius: 9999px;
          font-size: 12px;
          font-weight: 600;
          border: 1px solid;
          white-space: nowrap;
        }
        .claim-evidence {
          font-size: 13px;
          color: #8e8e93;
          margin-top: 3px;
          line-height: 1.5;
        }
        .claim-cite {
          display: inline-flex;
          align-items: center;
          gap: 4px;
          margin-left: 4px;
          color: #45515e;
          text-decoration: none;
          font-weight: 500;
          white-space: nowrap;
        }
        .claim-cite:hover { color: #0a0a0a; }
        .claim-cite:hover .cite-badge { background: #0a0a0a; color: #ffffff; }
        .cite-badge {
          display: inline-flex;
          align-items: center;
          justify-content: center;
          min-width: 16px;
          height: 16px;
          padding: 0 4px;
          border-radius: 4px;
          background: #eef0f3;
          color: #45515e;
          font-size: 11px;
          font-weight: 700;
          transition: background .15s, color .15s;
        }
        .claim-cite-plain { margin-left: 4px; }

        .stats-row {
          display: grid;
          grid-template-columns: repeat(4,1fr);
          gap: 12px;
          margin-bottom: 64px;
        }
        @media (max-width: 767px) { .stats-row { grid-template-columns: repeat(2,1fr); } }
        .stat-cell {
          border: 1px solid #e5e7eb;
          border-radius: 16px;
          padding: 24px;
          text-align: center;
        }
        .stat-num { font-size: 40px; font-weight: 600; letter-spacing: -1px; color: #0a0a0a; line-height: 1.2; }
        .stat-lbl { font-size: 14px; color: #5f5f5f; margin-top: 4px; }

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

        .cbot-fab {
          position: fixed; right: 24px; bottom: 24px; z-index: 60;
          background: #0a0a0a; color: #fff; border: none; border-radius: 9999px;
          padding: 14px 20px; font-size: 14px; font-weight: 600; cursor: pointer;
          box-shadow: rgba(0,0,0,.22) 0 10px 30px -6px; font-family: inherit;
          display: flex; align-items: center; gap: 8px; transition: transform .15s;
          animation: cbotPop .35s cubic-bezier(.22,.9,.3,1) both;
        }
        .cbot-fab:hover { transform: translateY(-1px); }
        @keyframes cbotPop {
          0% { opacity: 0; transform: translateY(12px) scale(.92); }
          100% { opacity: 1; transform: translateY(0) scale(1); }
        }
        .cbot-window {
          position: fixed; right: 24px; bottom: 84px; z-index: 60;
          width: 360px; max-width: calc(100vw - 32px);
          height: 460px; max-height: calc(100vh - 140px);
          background: #fff; border: 1px solid #eaecf0; border-radius: 16px;
          box-shadow: rgba(0,0,0,.18) 0 20px 50px -12px;
          display: flex; flex-direction: column; overflow: hidden;
          animation: cbotPop .3s cubic-bezier(.22,.9,.3,1) both;
        }
        .cbot-head { display: flex; align-items: center; justify-content: space-between; padding: 14px 16px; border-bottom: 1px solid #eaecf0; }
        .cbot-title { font-size: 14px; font-weight: 600; color: #0a0a0a; }
        .cbot-sub { font-size: 11px; color: #8e8e93; margin-top: 1px; }
        .cbot-x { background: none; border: none; color: #a8aab2; cursor: pointer; font-size: 15px; }
        .cbot-body { flex: 1; overflow-y: auto; padding: 14px; display: flex; flex-direction: column; gap: 10px; background: #fafafa; }
        .cbot-msg { display: flex; }
        .cbot-msg.user { justify-content: flex-end; }
        .cbot-msg.assistant { justify-content: flex-start; }
        .cbot-bubble { max-width: 84%; padding: 9px 12px; border-radius: 14px; font-size: 13px; line-height: 1.5; }
        .cbot-bubble.user { background: #0a0a0a; color: #fff; border-bottom-right-radius: 4px; }
        .cbot-bubble.assistant { background: #fff; color: #222222; border: 1px solid #eaecf0; border-bottom-left-radius: 4px; }
        .cbot-bubble.err { color: #dc2626; }
        .cbot-risk { display: inline-block; margin-top: 8px; padding: 2px 8px; border-radius: 9999px; border: 1px solid; font-size: 11px; font-weight: 600; }
        .cbot-src { display: flex; flex-direction: column; gap: 2px; margin-top: 6px; }
        .cbot-src a { font-size: 12px; color: #45515e; text-decoration: none; }
        .cbot-src a:hover { color: #0a0a0a; text-decoration: underline; }
        .cbot-typing { color: #8e8e93; font-style: italic; }
        .cbot-input { display: flex; gap: 8px; padding: 10px 12px; border-top: 1px solid #eaecf0; }
        .cbot-input input { flex: 1; border: 1px solid #eaecf0; border-radius: 9999px; padding: 9px 14px; font-size: 13px; font-family: inherit; outline: none; }
        .cbot-input input:focus { border-color: #0a0a0a; }
        .cbot-send { background: #0a0a0a; color: #fff; border: none; border-radius: 9999px; width: 36px; height: 36px; cursor: pointer; font-size: 16px; flex-shrink: 0; }
        .cbot-send:disabled { opacity: .4; cursor: not-allowed; }
        @media (max-width: 640px) { .cbot-window { right: 16px; left: 16px; width: auto; } }
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

        {/* Product carousel — all capabilities orbit on a shared ellipse */}
        <div className="orbit-stage">
          <div className="orbit-rail">
            {PRODUCT_CARDS.map((c, i) => (
              <div
                key={c.title}
                ref={(el) => {
                  cardRefs.current[i] = el;
                }}
                className="orbit-card"
                style={{ background: c.bg }}
              >
                <span className="orbit-glow" />
                <div className="orbit-title">{c.title}</div>
                <div className="orbit-desc">{c.desc}</div>
              </div>
            ))}
          </div>
          <div className="orbit-dots">
            {PRODUCT_CARDS.map((c, i) => (
              <span
                key={c.title}
                className={`orbit-dot${i === frontIdx ? " active" : ""}`}
                aria-label={c.title}
              />
            ))}
          </div>
        </div>

        {/* How it works */}
        <div className="how-grid">
          {HOW_IT_WORKS.map(({ step, title, desc }) => (
            <div className="how-cell" key={step}>
              <div className="how-step">{step}</div>
              <div className="how-title">{title}</div>
              <div className="how-desc">{desc}</div>
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
              <input value={url} onChange={(e) => setUrl(e.target.value)} placeholder="https://example.gov/policy or a PDF link" />
              <button onClick={() => ingestUrl()} disabled={ingesting || !url} className="btn-primary">
                {ingesting ? "Ingesting…" : "Ingest URL"}
              </button>
              <button onClick={resetUrl} className="btn-ghost">Clear</button>
              <button
                onClick={() => ingestUrl(DEMO_SOURCE_URL)}
                disabled={ingesting}
                style={{ background: "none", border: "none", padding: "8px 0 0", fontSize: 13, color: "#1d4ed8", cursor: "pointer", fontFamily: "inherit", textDecoration: "underline", textUnderlineOffset: 3 }}
              >
                No source handy? Load a demo source (GDPR)
              </button>
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
              {knowledgeSources.length > 0 && (
                <div style={{ marginTop: 14, paddingTop: 14, borderTop: "1px solid #eaecf0" }}>
                  <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 8 }}>
                    <p style={{ fontSize: 12, fontWeight: 600, textTransform: "uppercase", letterSpacing: ".02em", color: "#8e8e93", margin: 0 }}>
                      In the knowledge base
                    </p>
                    {isAdmin && (
                      <button
                        onClick={exitAdmin}
                        title="You are curating the knowledge base. Click to exit admin mode."
                        style={{ background: "#eef0f3", border: "none", borderRadius: 9999, color: "#45515e", cursor: "pointer", fontSize: 11, fontWeight: 600, padding: "2px 8px", lineHeight: 1.4 }}
                      >
                        Admin ✕
                      </button>
                    )}
                  </div>
                  <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
                    {knowledgeSources.map((src) => (
                      <div key={src.source_url} style={{ display: "flex", alignItems: "center", gap: 8, fontSize: 13 }}>
                        <span style={{ flex: 1, color: "#45515e", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }} title={src.source_url}>
                          {src.source_title || src.source_url}
                        </span>
                        <span style={{ color: "#a8aab2", fontSize: 12, flexShrink: 0 }}>{src.chunks} chunks</span>
                        {isAdmin && (
                          <button
                            onClick={() => deleteKnowledgeSource(src.source_url)}
                            title="Remove source"
                            style={{ background: "none", border: "none", color: "#a8aab2", cursor: "pointer", fontSize: 14, padding: "0 2px", lineHeight: 1 }}
                          >
                            ✕
                          </button>
                        )}
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>

            <div className="card">
              <p className="lbl">Ask a Question</p>
              <textarea value={question} onChange={(e) => setQuestion(e.target.value)} rows={7} placeholder="Ask a governance, policy, or compliance question…" style={{ resize: "vertical" }} />
              <button onClick={() => analyzeQuestion()} disabled={loading || !question} className="btn-primary">
                {loading ? "Analyzing…" : "Analyze Query"}
              </button>
              <button onClick={resetQuery} className="btn-ghost">Clear</button>
              {trickQuestions.length > 0 && (
                <div style={{ marginTop: 14, paddingTop: 14, borderTop: "1px solid #eaecf0" }}>
                  <p style={{ fontSize: 12, fontWeight: 600, textTransform: "uppercase", letterSpacing: ".02em", color: "#8e8e93", marginBottom: 4 }}>
                    Try to trick it
                  </p>
                  <p style={{ fontSize: 12, color: "#a8aab2", marginBottom: 8, lineHeight: 1.5 }}>
                    Generated from your source — these sound answerable, but aren't. Watch the risk flag fire.
                  </p>
                  <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
                    {trickQuestions.map((tq) => (
                      <button key={tq} className="trick-pill" disabled={loading} onClick={() => analyzeQuestion(tq)}>
                        {tq}
                      </button>
                    ))}
                  </div>
                </div>
              )}
            </div>
          </div>

          {/* Right */}
          <div>
            {analyzeError && (
              <div style={{ marginBottom: 14, padding: "12px 16px", background: "#fef2f2", border: "1px solid #fca5a5", borderRadius: 12, fontSize: 13, color: "#dc2626", fontWeight: 500 }}>
                {analyzeError}
              </div>
            )}
            {loading ? (
              <div className="card empty-state">
                <div style={{ display: "flex", flexDirection: "column", gap: 10, alignItems: "flex-start" }}>
                  {PIPELINE_STAGES.map((stage, i) => (
                    <div key={stage} style={{ display: "flex", alignItems: "center", gap: 10, fontSize: 14 }}>
                      <span style={{
                        width: 22, height: 22, borderRadius: 9999, display: "inline-flex", alignItems: "center", justifyContent: "center",
                        fontSize: 12, fontWeight: 600,
                        background: i < pipelineStage ? "#0a0a0a" : i === pipelineStage ? "#e5e7eb" : "#f7f8fa",
                        color: i < pipelineStage ? "#ffffff" : "#5f5f5f",
                        border: i === pipelineStage ? "1px solid #0a0a0a" : "1px solid #e5e7eb",
                      }}>
                        {i < pipelineStage ? "✓" : i + 1}
                      </span>
                      <span style={{
                        color: i === pipelineStage ? "#0a0a0a" : i < pipelineStage ? "#45515e" : "#a8aab2",
                        fontWeight: i === pipelineStage ? 600 : 400,
                      }}>
                        {stage}{i === pipelineStage ? "…" : ""}
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            ) : !result ? (
              <div className="card empty-state">
                <div style={{ fontSize: 28, color: "#a8aab2" }}>◎</div>
                <div style={{ fontWeight: 600, color: "#45515e", fontSize: 16 }}>Ready for analysis</div>
                <div style={{ fontSize: 14, color: "#8e8e93", maxWidth: 280, lineHeight: 1.6 }}>
                  Ask a question to see a grounded answer, claim-level verification, risk level, and sources.
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

                  {result.claim_verification?.length > 0 && (
                    <div style={{ marginTop: 16 }}>
                      <p className="lbl" style={{ marginBottom: 10 }}>Claim Verification</p>
                      <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
                        {result.claim_verification.map((c: any, i: number) => {
                          const v = (c.verdict === "entailed" || c.verdict === "supported")
                            ? { icon: "✓", label: "Entailed", color: "#1ba673", bg: "#e8ffea", border: "#b5e8c4" }
                            : (c.verdict === "baseless" || c.verdict === "partial")
                            ? { icon: "~", label: "Not in context", color: "#d97706", bg: "#fffbeb", border: "#fcd34d" }
                            : { icon: "✕", label: "Contradicted", color: "#dc2626", bg: "#fef2f2", border: "#fca5a5" };
                          // Link each claim's evidence to the same numbered
                          // source shown in the Sources panel below.
                          const srcIdx = (result.sources ?? []).findIndex(
                            (s: any) => s.title && s.title === c.source_title
                          );
                          const cite =
                            srcIdx >= 0
                              ? { num: srcIdx + 1, url: result.sources[srcIdx].url }
                              : null;
                          return (
                            <div key={i} className="claim-row">
                              <span className="claim-chip" style={{ color: v.color, background: v.bg, borderColor: v.border }}>
                                {v.icon} {v.label}
                              </span>
                              <div style={{ flex: 1 }}>
                                <div style={{ fontSize: 14, color: "#222222", lineHeight: 1.5 }}>{c.claim}</div>
                                {c.evidence && (
                                  <div className="claim-evidence">
                                    “{c.evidence}”
                                    {c.source_title &&
                                      (cite ? (
                                        <a
                                          href={cite.url}
                                          target="_blank"
                                          rel="noopener noreferrer"
                                          className="claim-cite"
                                          title={`Source ${cite.num}: ${c.source_title}`}
                                        >
                                          <span className="cite-badge">{cite.num}</span>
                                          {c.source_title}
                                        </a>
                                      ) : (
                                        <span className="claim-cite-plain">— {c.source_title}</span>
                                      ))}
                                  </div>
                                )}
                              </div>
                            </div>
                          );
                        })}
                      </div>
                    </div>
                  )}
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

        {/* Accuracy stats */}
        {stats && (
          <div className="stats-row">
            <div className="stat-cell">
              <div className="stat-num">{stats.total_queries}</div>
              <div className="stat-lbl">Queries analyzed</div>
            </div>
            <div className="stat-cell">
              <div className="stat-num" style={{ color: "#1ba673" }}>{stats.grounded_pct ?? "—"}%</div>
              <div className="stat-lbl">Fully grounded</div>
            </div>
            <div className="stat-cell">
              <div className="stat-num" style={{ color: "#d97706" }}>{stats.risk_counts?.Medium ?? 0}</div>
              <div className="stat-lbl">Medium risk flagged</div>
            </div>
            <div className="stat-cell">
              <div className="stat-num" style={{ color: "#dc2626" }}>{stats.risk_counts?.High ?? 0}</div>
              <div className="stat-lbl">High risk caught</div>
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
              <a className="footer-link" href="/docs">Documentation</a>
              <a className="footer-link" href="mailto:m.haseeb311@gmail.com">Contact</a>
              <span className="footer-micro" style={{ alignSelf: "center" }}>© {new Date().getFullYear()} TrustGuard AI. All rights reserved.</span>
            </div>
          </div>
        </div>
      </footer>
        {result && (
          <>
            {chatOpen && (
              <div className="cbot-window">
                <div className="cbot-head">
                  <div>
                    <div className="cbot-title">Guardian</div>
                    <div className="cbot-sub">Grounded follow-up assistant · risk-scored from your sources</div>
                  </div>
                  <button className="cbot-x" onClick={() => setChatOpen(false)} aria-label="Close follow-up chat">✕</button>
                </div>
                <div className="cbot-body" ref={chatBodyRef}>
                  {chatMessages.map((m, i) => {
                    const r = m.risk ? (riskStyles[m.risk] ?? riskStyles["Low"]) : null;
                    return (
                      <div key={i} className={`cbot-msg ${m.role}`}>
                        <div className={`cbot-bubble ${m.role}${m.error ? " err" : ""}`}>
                          {m.text}
                          {m.role === "assistant" && r && (
                            <span className="cbot-risk" style={{ color: r.color, background: r.bg, borderColor: r.border }}>
                              {m.risk} risk
                            </span>
                          )}
                          {m.role === "assistant" && m.sources?.length > 0 && (
                            <div className="cbot-src">
                              {m.sources.slice(0, 3).map((s: any, j: number) => (
                                <a key={j} href={s.url} target="_blank" rel="noopener noreferrer">
                                  [{j + 1}] {s.title || "Source"}
                                </a>
                              ))}
                            </div>
                          )}
                        </div>
                      </div>
                    );
                  })}
                  {chatLoading && (
                    <div className="cbot-msg assistant">
                      <div className="cbot-bubble assistant cbot-typing">Analyzing…</div>
                    </div>
                  )}
                </div>
                <div className="cbot-input">
                  <input
                    value={chatInput}
                    onChange={(e) => setChatInput(e.target.value)}
                    onKeyDown={(e) => { if (e.key === "Enter") sendFollowUp(); }}
                    placeholder="Ask Guardian a follow-up…"
                    disabled={chatLoading}
                  />
                  <button className="cbot-send" onClick={sendFollowUp} disabled={chatLoading || !chatInput.trim()} aria-label="Send follow-up">→</button>
                </div>
              </div>
            )}

            <button className="cbot-fab" onClick={() => setChatOpen((o) => !o)} aria-label="Ask Guardian a follow-up question">
              {chatOpen ? "✕ Close" : "💬 Ask Guardian"}
            </button>
          </>
        )}
    </main>
  );
}
