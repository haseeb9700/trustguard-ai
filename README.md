# TrustGuard AI

**Enterprise AI Governance & Hallucination Detection Platform**

TrustGuard AI is a full-stack AI governance platform that uses Retrieval-Augmented Generation (RAG), vector databases, hallucination detection, risk scoring, feedback learning, and audit logging to make LLM responses more trustworthy and explainable.

---

## Features

- Dynamic URL ingestion for trusted policy documents
- RAG-based question answering
- Semantic search using vector embeddings
- Reranking for improved retrieval accuracy
- Hallucination detection
- Risk scoring: Low / Medium / High
- Audit logging for governance traceability
- Human feedback collection
- Full-stack dashboard using Next.js and FastAPI

---

## Problem Statement

Large Language Models can generate confident but unsupported answers. In compliance-heavy domains like immigration, AI governance, finance, and healthcare, hallucinated information can create serious risk.

TrustGuard AI solves this by grounding responses in trusted documents, evaluating hallucination risk, assigning governance scores, and logging every interaction.

---

## Architecture

```text
User
 ↓
Next.js Frontend
 ↓
FastAPI Backend
 ↓
URL Ingestion / Web Scraping
 ↓
Chunking + Embeddings
 ↓
ChromaDB Vector Store
 ↓
RAG Retrieval + Reranking
 ↓
OpenAI Response Generation
 ↓
Hallucination Evaluation
 ↓
Risk Scoring
 ↓
Audit Logs + Feedback Dataset
