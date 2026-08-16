"use client";

import { KeyboardEvent, useEffect, useState } from "react";
import { getOutputs, RenderedOutput } from "@/lib/api";
import { RewriteRationale } from "./rewrite-rationale";

const outputLabels: Record<string, string> = { clean_version: "정리본", executive_summary: "요약본", action_decision_sheet: "실행안" };
function outputLabel(output: RenderedOutput) { return outputLabels[output.output_type] ?? output.output_type; }

/** Lines are emitted one per source slot, so they split back into discrete items. */
function itemsOf(text: string): string[] {
  return text.split("\n").map((line) => line.trim()).filter(Boolean);
}

export function DiagnosisWorkspace({ documentId }: { documentId: string }) {
  const [outputs, setOutputs] = useState<RenderedOutput[]>([]);
  const [activeOutputId, setActiveOutputId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let active = true;
    setOutputs([]); setActiveOutputId(null); setError(null); setLoading(true);
    getOutputs(documentId)
      .then((next) => { if (!active) return; setOutputs(next.outputs); setActiveOutputId(next.outputs[0]?.id ?? null); setLoading(false); })
      .catch((cause) => { if (active) { setError(cause instanceof Error ? cause.message : "문서를 불러오지 못했습니다."); setLoading(false); } });
    return () => { active = false; };
  }, [documentId]);

  function onTabKeyDown(event: KeyboardEvent<HTMLButtonElement>, index: number) {
    let nextIndex = index;
    if (event.key === "ArrowRight") nextIndex = (index + 1) % outputs.length;
    else if (event.key === "ArrowLeft") nextIndex = (index - 1 + outputs.length) % outputs.length;
    else if (event.key === "Home") nextIndex = 0;
    else if (event.key === "End") nextIndex = outputs.length - 1;
    else return;
    event.preventDefault();
    setActiveOutputId(outputs[nextIndex].id);
    const tabs = event.currentTarget.parentElement?.querySelectorAll<HTMLButtonElement>('[role="tab"]');
    tabs?.[nextIndex]?.focus();
  }

  const activeOutput = outputs.find((output) => output.id === activeOutputId) ?? null;

  if (error) return <main className="doc-shell"><p role="alert">{error}</p></main>;
  if (loading) return <main className="doc-shell"><p aria-live="polite">문서를 정리하는 중…</p></main>;

  return <main className="doc-shell">
    <header className="doc-head">
      <a href="/">← 새 분석</a>
      {outputs.length > 1 && <div className="segmented-control" role="tablist" aria-label="문서 형태">
        {outputs.map((output, index) => {
          const active = output.id === activeOutputId;
          return <button key={output.id} id={`output-tab-${output.id}`} type="button" role="tab" aria-selected={active}
            aria-controls={`output-panel-${output.id}`} tabIndex={active ? 0 : -1}
            onClick={() => setActiveOutputId(output.id)} onKeyDown={(event) => onTabKeyDown(event, index)}>{outputLabel(output)}</button>;
        })}
      </div>}
    </header>

    {activeOutput ? <>
      <article id={`output-panel-${activeOutput.id}`} role="tabpanel" aria-labelledby={`output-tab-${activeOutput.id}`} className="doc-body">
        <h1>{outputLabel(activeOutput)}</h1>
        {activeOutput.sections.map((section, index) => <section key={`${section.heading}-${index}`} className="doc-section">
          <h2>{section.heading}</h2>
          <ul>{itemsOf(section.text).map((item, itemIndex) => <li key={itemIndex}>{item}</li>)}</ul>
        </section>)}
      </article>
      <RewriteRationale documentId={documentId} outputType={activeOutput.output_type} />
    </> : <div className="empty-output" role="status">
      <p>정리된 문서가 아직 없습니다.</p>
    </div>}
  </main>;
}
