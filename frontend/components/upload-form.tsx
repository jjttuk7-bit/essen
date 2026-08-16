"use client";

import { ChangeEvent, FormEvent, useId, useState } from "react";
import { useRouter } from "next/navigation";

import { analyzeDocument, uploadDocument } from "@/lib/api";

const ACCEPTED_EXTENSIONS = ["txt", "md", "markdown", "pdf"];

function formatBytes(bytes: number): string {
  return `${(bytes / (1024 * 1024)).toFixed(bytes < 1024 * 1024 ? 1 : 0)} MB`;
}

export function UploadForm() {
  const inputId = useId();
  const router = useRouter();
  const [file, setFile] = useState<File | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [status, setStatus] = useState<"idle" | "uploading" | "analyzing">("idle");
  const busy = status !== "idle";

  function onFileChange(event: ChangeEvent<HTMLInputElement>) {
    const candidate = event.target.files?.[0] ?? null;
    setError(null);
    if (candidate && !ACCEPTED_EXTENSIONS.includes(candidate.name.split(".").pop()?.toLowerCase() ?? "")) {
      setFile(null);
      setError("TXT, Markdown, or PDF 파일만 분석할 수 있습니다.");
      return;
    }
    setFile(candidate);
  }

  async function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (status !== "idle") return;
    if (!file) {
      setError("분석할 문서를 먼저 선택해 주세요.");
      return;
    }
    try {
      setError(null);
      setStatus("uploading");
      const uploaded = await uploadDocument(file);
      setStatus("analyzing");
      await analyzeDocument(uploaded.document_id);
      router.push(`/documents/${uploaded.document_id}`);
    } catch (cause) {
      setStatus("idle");
      setError(cause instanceof Error ? cause.message : "문서를 분석하지 못했습니다. 다시 시도해 주세요.");
    }
  }

  const statusMessage = status === "uploading" ? "문서를 읽고 있습니다…" : status === "analyzing" ? "의미와 근거를 분석하고 있습니다…" : "";

  return (
    <form className="upload-form" onSubmit={onSubmit} noValidate>
      <label className="file-drop" htmlFor={inputId}>
        <span className="file-icon" aria-hidden="true">↗</span>
        <span className="file-prompt">{file ? file.name : "분석할 문서를 놓거나 선택하세요"}</span>
        <span className="file-hint">TXT · Markdown · PDF · 최대 10MB</span>
      </label>
      <input id={inputId} name="document" className="sr-only" type="file" accept=".txt,.md,.markdown,.pdf" onChange={onFileChange} />
      {file && <p className="selection" aria-label="Selected file">{file.name} <span>{formatBytes(file.size)}</span></p>}
      <button className="analyze-button" type="submit" disabled={busy} aria-busy={busy} aria-label="Analyze document" aria-describedby={error ? "upload-error" : undefined}>
        {busy ? "분석 준비 중" : "Analyze document"} <span aria-hidden="true">→</span>
      </button>
      <p className="status" aria-live="polite">{statusMessage}</p>
      {error && <p id="upload-error" className="form-error" role="alert">{error}</p>}
    </form>
  );
}
