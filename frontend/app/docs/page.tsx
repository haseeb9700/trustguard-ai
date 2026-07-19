"use client";

type Section = {
  id: string;
  title: string;
  tag: string;
  paras: string[];
};

const SECTIONS: Section[] = [
  {
    id: "overview",
    title: "What TrustGuard is",
    tag: "Overview",
    paras: [
      "TrustGuard AI is an AI-governance layer for question answering. Large language models produce fluent, confident text whether or not it is true, which is dangerous in compliance-heavy domains like immigration, finance, healthcare, and AI policy. TrustGuard constrains a model to answer only from a curated set of trusted documents, then inspects, scores, and logs every answer.",
      "The guiding principle is simple: an answer is only trustworthy if you can trace it back to a source. Every part of the system exists to make that traceability real — to ground answers in evidence, to detect when a claim is not supported, to rate the governance risk of each response, and to keep a complete audit trail.",
      "This page explains how the moving parts work and what each is for. It focuses on the reasoning, retrieval, verification, evaluation, and security machinery rather than interface or plumbing details.",
    ],
  },
  {
    id: "pipeline",
    title: "The multi-agent workflow",
    tag: "Architecture",
    paras: [
      "A question flows through a sequence of specialized steps, each with a single responsibility. First the query is rewritten for retrieval, then relevant chunks are retrieved and reranked, then an answer is generated strictly from those chunks. The answer is checked two ways in parallel — a holistic hallucination score and a claim-by-claim verification — and the results are combined into a governance risk rating. Finally, the entire outcome is written to an audit log.",
      "Splitting the work into focused stages keeps each step simple to reason about, test, and improve in isolation. The holistic evaluation and the claim verification are independent given the answer, so they run concurrently to cut end-to-end latency.",
      "The order is: query rewrite → retrieval → reranking → answer generation → (hallucination evaluation ∥ claim verification) → risk scoring → audit logging.",
    ],
  },
  {
    id: "rewrite",
    title: "Query rewriting",
    tag: "Retrieval",
    paras: [
      "Users ask questions casually (\"can I chill for a few months without a job on OPT?\"). Semantic search works far better on precise, formal phrasing. The query-rewrite step reformulates the raw question into a retrieval-friendly query that preserves the original intent while expanding vague language into the terminology the source documents actually use.",
      "It is guided by few-shot examples of good rewrites, and it is explicitly instructed never to answer the question — only to reshape it for search.",
    ],
  },
  {
    id: "retrieval",
    title: "Retrieval and reranking",
    tag: "Retrieval",
    paras: [
      "Each trusted document is split into overlapping, section-aware chunks and embedded into vectors using a sentence-transformer embedding model. At query time the rewritten query is embedded the same way, and the chunks are ranked by cosine similarity to build a wide candidate pool.",
      "A wide pool has good recall but noisy ordering, so a second, more precise model — a cross-encoder reranker — re-scores the top candidates by reading the query and each chunk together. This two-stage design (cheap recall, then expensive precision) is standard in production retrieval and materially improves which evidence reaches the answer step.",
      "Because retrieval determines the ceiling on answer quality, it is measured on its own (see Evaluation).",
    ],
  },
  {
    id: "answer",
    title: "Grounded answer generation",
    tag: "Generation",
    paras: [
      "The answer model receives only the reranked chunks and is instructed to answer strictly from them. If the evidence does not support an answer, it must say \"I could not verify this from the provided sources\" rather than guess. Refusing to answer is treated as a correct, safe outcome — not a failure.",
      "The prompt also hardens against prompt injection: because source text is untrusted, the model is told to treat everything in the provided context as reference data only and to ignore any instructions embedded inside it (for example \"ignore previous instructions\").",
    ],
  },
  {
    id: "verification",
    title: "Claim-level hallucination detection",
    tag: "Verification",
    paras: [
      "Scoring a whole answer as \"hallucinated or not\" is weak: a mostly-correct answer with one fabricated detail scores as fine. TrustGuard instead decomposes each answer into atomic claims and verifies each claim against the evidence, an approach inspired by hierarchical retromorphic verification research (RT4CHART).",
      "The answer is first split into self-contained claims without showing the model the context, so claim formation stays faithful to the answer rather than being biased by the evidence. Each claim is then screened locally against every retrieved chunk and merged with an OR-join (one supporting chunk suffices; any contradicting chunk dominates). Claims that are not locally settled are re-verified globally against the full context, which catches evidence spread across chunk boundaries.",
      "Every claim ends up labeled entailed (the source supports it), baseless (the source says nothing about it), or contradicted (the source says the opposite). Baseless claims are stripped of any evidence quote, so the system never pretends to support something it cannot.",
    ],
  },
  {
    id: "risk",
    title: "Governance risk scoring",
    tag: "Governance",
    paras: [
      "The per-claim verdicts are collapsed into a single governance rating using an AND-join: the whole answer is only as trustworthy as its weakest claim. A single contradicted claim marks the answer High risk, because the sources state the opposite of what was generated. A single baseless claim raises the floor to Medium. An answer whose claims are all entailed, with a clean hallucination score, is Low risk.",
      "This rule-based rating is deliberately transparent and explainable — each rating comes with a human-readable reason — which matters for a governance tool where decisions must be defensible.",
    ],
  },
  {
    id: "quality-model",
    title: "Learned answer-quality model",
    tag: "Machine learning",
    paras: [
      "Alongside the rule-based risk score, a machine-learning model predicts the probability that a human would judge an answer correct. Crucially, it does not try to learn the answers themselves — fine-tuning a generator to memorize answers would reintroduce the very hallucination risk the product prevents. Instead it learns a quality/reward model over the signals the pipeline already produces.",
      "Its features are the hallucination score, the risk score, the number of entailed / baseless / contradicted claims, the fraction of entailed claims, the retrieved-context count, the number of sources, answer length, and whether the answer was an explicit non-answer. The label is the human feedback (correct, or not). A scaled logistic regression is the default because its coefficients are interpretable — you can explain why an answer was flagged — with gradient boosting available as an alternative.",
      "On the bootstrap dataset it reaches roughly 0.90 accuracy and 0.86 ROC-AUC against a 0.63 majority baseline, and the learned weights are sensible: a high fraction of entailed claims pushes quality up, while contradicted claims and non-answers push it down. As real feedback accumulates, retraining on it is the system's concrete \"learn and improve\" loop.",
    ],
  },
  {
    id: "audit",
    title: "Audit logging and feedback",
    tag: "Governance",
    paras: [
      "Every analyzed question — including cache hits — is persisted with its answer, hallucination analysis, and risk decision, so there is a complete, queryable trail of what was asked, what was answered, and how it was rated. This is the backbone of governance: accountability requires a record.",
      "Humans can rate each answer correct, partially correct, or incorrect, and supply a corrected answer. That feedback both surfaces on the live accuracy dashboard and becomes training data for the quality model.",
    ],
  },
  {
    id: "caching",
    title: "Caching",
    tag: "Performance",
    paras: [
      "Repeated questions should not re-run the entire pipeline. Two in-memory caches with size and time limits handle this: an answer cache keyed by the normalized question returns a full prior result, and an embedding cache stores query embeddings by text.",
      "Because answers depend on the knowledge base, the answer cache is cleared automatically whenever a source is ingested or deleted, so cached answers can never go stale against the current evidence. Query embeddings are independent of the knowledge base, so that cache persists across ingestions. The audit log is still written on cache hits, keeping the governance trail complete.",
    ],
  },
  {
    id: "security",
    title: "Security model",
    tag: "Security",
    paras: [
      "Because the system fetches user-supplied URLs, it defends against server-side request forgery (SSRF). A guard rejects any URL that resolves to a private, loopback, link-local, reserved, or metadata address. Redirects are followed manually and re-validated at every hop, so a public URL cannot bounce the server to an internal one. The validated IP is pinned for the duration of the fetch, closing the DNS-rebinding window where a hostname flips from a public to an internal address between validation and connection. Fetched documents are size-capped to prevent memory exhaustion.",
      "Answer generation is hardened against prompt injection from source text. Requests are rate-limited, inputs are length-capped, and knowledge-base changes (ingesting or deleting sources) are gated behind an admin key so ordinary visitors see a read-only, tamper-proof source list.",
    ],
  },
  {
    id: "evaluation",
    title: "Evaluation",
    tag: "Measurement",
    paras: [
      "A system that claims to be trustworthy has to prove it with numbers, so both halves of the pipeline are benchmarked against labeled datasets. Retrieval is measured with hit-rate@k, recall@k, precision@k, MRR, and nDCG@k against a corpus with known relevant chunks — queries are deliberately paraphrased so surface-word overlap alone cannot solve them, which exposes the value of semantic retrieval over a lexical baseline.",
      "The claim verifier is measured with per-verdict precision, recall, and F1 plus a confusion matrix, aggregating claim verdicts to an answer-level judgment exactly as production does. Each harness ships an offline lexical baseline (the floor the real system should beat) and an oracle (which verifies the scoring math), so results are reproducible without a model or database.",
    ],
  },
  {
    id: "followup",
    title: "Guardian follow-up assistant",
    tag: "Assistance",
    paras: [
      "After a question is analyzed, a follow-up assistant named Guardian becomes available. Every follow-up runs through the same full pipeline — retrieval, verification, and risk scoring — rather than becoming free-form chat. This keeps follow-up answers grounded and risk-scored, so the assistant inherits the same guarantees as the primary flow and cannot quietly hallucinate.",
    ],
  },
  {
    id: "knowledge",
    title: "Knowledge-base curation",
    tag: "Data",
    paras: [
      "The knowledge base is the single source of truth for every answer, so what goes into it is a governance decision. Ingesting a source scrapes the page or PDF, splits it into section-aware chunks, embeds them, and stores them as the only evidence the system may cite. Sources are curated by an administrator; end users can see exactly what is in the knowledge base but cannot alter it, which makes the boundary of the system's knowledge visible and its contents tamper-proof.",
    ],
  },
];

export default function DocsPage() {
  return (
    <main className="doc">
      <style jsx>{`
        .doc {
          max-width: 860px;
          margin: 0 auto;
          padding: 48px 24px 96px;
          color: #1a1a1a;
        }
        .back { font-size: 14px; color: #8e8e93; text-decoration: none; }
        .back:hover { color: #0a0a0a; }
        .doc-h1 { font-size: 40px; font-weight: 700; letter-spacing: -.03em; margin: 20px 0 8px; }
        .doc-lead { font-size: 17px; line-height: 1.6; color: #5f5f5f; margin: 0 0 40px; }
        .toc {
          border: 1px solid #eaecf0; border-radius: 14px; padding: 20px 24px; margin-bottom: 48px;
          background: #fafafa;
        }
        .toc-title { font-size: 12px; font-weight: 700; text-transform: uppercase; letter-spacing: .04em; color: #8e8e93; margin: 0 0 12px; }
        .toc-list { display: grid; grid-template-columns: 1fr 1fr; gap: 8px 24px; }
        .toc-link { font-size: 14px; color: #45515e; text-decoration: none; }
        .toc-link:hover { color: #0a0a0a; text-decoration: underline; }
        .sec { padding: 28px 0; border-top: 1px solid #eaecf0; scroll-margin-top: 24px; }
        .sec-tag { display: inline-block; font-size: 11px; font-weight: 700; text-transform: uppercase; letter-spacing: .05em; color: #a855f7; margin-bottom: 8px; }
        .sec-h { font-size: 24px; font-weight: 600; letter-spacing: -.02em; margin: 0 0 14px; }
        .sec-p { font-size: 15.5px; line-height: 1.72; color: #333333; margin: 0 0 14px; }
        .sec-p:last-child { margin-bottom: 0; }
        .foot { margin-top: 48px; font-size: 14px; color: #8e8e93; }
        .foot a { color: #45515e; text-decoration: none; }
        .foot a:hover { color: #0a0a0a; }
        @media (max-width: 600px) { .toc-list { grid-template-columns: 1fr; } .doc-h1 { font-size: 32px; } }
      `}</style>

      <a className="back" href="/">← Back to TrustGuard</a>
      <h1 className="doc-h1">How TrustGuard works</h1>
      <p className="doc-lead">
        A walkthrough of the reasoning, retrieval, verification, evaluation, and security
        that turn a language model into an auditable, source-grounded governance system.
      </p>

      <div className="toc">
        <p className="toc-title">Contents</p>
        <div className="toc-list">
          {SECTIONS.map((s) => (
            <a key={s.id} className="toc-link" href={`#${s.id}`}>
              {s.title}
            </a>
          ))}
        </div>
      </div>

      {SECTIONS.map((s) => (
        <section key={s.id} id={s.id} className="sec">
          <span className="sec-tag">{s.tag}</span>
          <h2 className="sec-h">{s.title}</h2>
          {s.paras.map((p, i) => (
            <p key={i} className="sec-p">{p}</p>
          ))}
        </section>
      ))}

      <p className="foot">
        Built by Mohammed Abdul Haseeb · <a href="/">Return to the app</a>
      </p>
    </main>
  );
}
