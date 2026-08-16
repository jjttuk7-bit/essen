"use client";

import { useEffect, useState } from "react";
import { DiffResponse, getDiff, getOutputs, RenderedOutput } from "@/lib/api";
import { DocumentIdentity } from "./document-identity";
import { RewriteRationale } from "./rewrite-rationale";

const DOCUMENT_TITLE = "정리된 문서";

/** Lines are emitted one per source slot, so they split back into discrete items. */
function itemsOf(text: string): string[] {
  return text.split("\n").map((line) => line.trim()).filter(Boolean);
}

export function DiagnosisWorkspace({ documentId }: { documentId: string }) {
  const [outputs, setOutputs] = useState<RenderedOutput[]>([]);
  const [activeOutputId, setActiveOutputId] = useState<string | null>(null);
  const [diff, setDiff] = useState<DiffResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let active = true;
    setOutputs([]); setActiveOutputId(null); setDiff(null); setError(null); setLoading(true);
    getOutputs(documentId)
      .then((next) => {
        if (!active) return;
        setOutputs(next.outputs); setActiveOutputId(next.outputs[0]?.id ?? null); setLoading(false);
        const first = next.outputs[0];
        // Fetched once here: the identity heads the page and the rationale closes it.
        if (first) getDiff(documentId, first.output_type).then((body) => { if (active) setDiff(body); }).catch(() => undefined);
      })
      .catch((cause) => { if (active) { setError(cause instanceof Error ? cause.message : "문서를 불러오지 못했습니다."); setLoading(false); } });
    return () => { active = false; };
  }, [documentId]);

  const activeOutput = outputs.find((output) => output.id === activeOutputId) ?? null;

  if (error) return <main className="doc-shell"><p role="alert">{error}</p></main>;
  if (loading) return <main className="doc-shell"><p aria-live="polite">문서를 정리하는 중…</p></main>;

  return <main className="doc-shell">
    <header className="doc-head">
      <a href="/">← 새 분석</a>
    </header>

    {activeOutput ? <>
      {diff && <DocumentIdentity identity={diff.identity} />}
      <article className="doc-body" aria-label={DOCUMENT_TITLE}>
        <h1>{DOCUMENT_TITLE}</h1>
        {activeOutput.sections.map((section, index) => <section key={`${section.heading}-${index}`} className="doc-section">
          <h2>{section.heading}</h2>
          <ul>{itemsOf(section.text).map((item, itemIndex) => <li key={itemIndex}>{item}</li>)}</ul>
        </section>)}
      </article>
      {diff && <RewriteRationale diff={diff} />}
    </> : <div className="empty-output" role="status">
      <p>정리된 문서가 아직 없습니다.</p>
    </div>}
  </main>;
}
