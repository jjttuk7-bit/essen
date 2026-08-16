"use client";

import { KeyboardEvent, useEffect, useState } from "react";
import { Diagnosis, getDiagnosis, getOutputs, getSemanticMap, RenderedOutput, SemanticMap } from "@/lib/api";
import { DiffView } from "./diff-view";

const scoreCards: Array<[keyof Pick<Diagnosis, "signal_ratio" | "redundancy_ratio" | "evidence_coverage" | "decision_completeness">, string]> = [["signal_ratio", "Signal ratio"], ["redundancy_ratio", "Redundancy"], ["evidence_coverage", "Evidence"], ["decision_completeness", "Decision"]];
const outputLabels: Record<string, string> = { clean_version: "Clean brief", executive_summary: "Executive brief", action_decision_sheet: "Action plan" };
function outputLabel(output: RenderedOutput) { return outputLabels[output.output_type] ?? output.output_type; }

export function DiagnosisWorkspace({ documentId }: { documentId: string }) {
  const [diagnosis, setDiagnosis] = useState<Diagnosis | null>(null);
  const [semanticMap, setSemanticMap] = useState<SemanticMap | null>(null);
  const [outputs, setOutputs] = useState<RenderedOutput[]>([]);
  const [activeOutputId, setActiveOutputId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    setDiagnosis(null); setSemanticMap(null); setOutputs([]); setActiveOutputId(null); setError(null);
    Promise.all([getDiagnosis(documentId), getSemanticMap(documentId), getOutputs(documentId)])
      .then(([nextDiagnosis, nextMap, nextOutputs]) => { if (!active) return; setDiagnosis(nextDiagnosis); setSemanticMap(nextMap); setOutputs(nextOutputs.outputs); setActiveOutputId(nextOutputs.outputs[0]?.id ?? null); })
      .catch((cause) => { if (active) setError(cause instanceof Error ? cause.message : "결과를 불러오지 못했습니다."); });
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

  if (error) return <main className="result-shell"><p role="alert">{error}</p></main>;
  if (!diagnosis || !semanticMap) return <main className="result-shell"><p aria-live="polite">문서 진단을 불러오는 중…</p></main>;

  return <main className="result-shell">
    <header className="result-head"><a href="/">← New analysis</a><p>DOCUMENT / {documentId.slice(0, 8)}</p></header>
    <section className="result-summary" aria-labelledby="decision-readiness-title"><div><p className="eyebrow">DECISION READINESS</p><h1 id="decision-readiness-title"><span>{diagnosis.document_signal_score}</span><small>/ 100</small></h1><p>문서에서 지금 결정에 사용할 수 있는 신호와 근거의 준비도를 표시합니다.</p></div><div className="readiness-meta"><p className="eyebrow">OPEN GAPS</p><div className="gap-list">{diagnosis.gaps.length ? diagnosis.gaps.map((gap) => <span key={gap}>{gap}</span>) : <span>NONE</span>}</div></div></section>
    <section className="score-grid" aria-label="Document quality scores">{scoreCards.map(([key, label]) => <article key={key} className="score-tile"><p>{label}</p><strong>{Math.round(diagnosis[key] * 100)}%</strong></article>)}</section>
    <div className="decision-grid">
      <section className="output-workspace" aria-labelledby="output-title">
        <div className="workspace-title-row"><div><p className="eyebrow">DECISION BRIEF</p><h2 id="output-title">검토용 출력</h2></div>{outputs.length > 0 && <div className="segmented-control" role="tablist" aria-label="Output mode">{outputs.map((output, index) => { const active = output.id === activeOutputId; const tabId = `output-tab-${output.id}`; return <button key={output.id} id={tabId} type="button" role="tab" aria-selected={active} aria-controls={`output-panel-${output.id}`} tabIndex={active ? 0 : -1} onClick={() => setActiveOutputId(output.id)} onKeyDown={(event) => onTabKeyDown(event, index)}>{outputLabel(output)}</button>; })}</div>}</div>
        {outputs.length > 0 ? outputs.map((output) => <article key={output.id} id={`output-panel-${output.id}`} role="tabpanel" aria-labelledby={`output-tab-${output.id}`} className="brief-panel" hidden={output.id !== activeOutputId}><div className="audit-metadata" aria-label="Render metadata"><span>Version {output.version}</span><span>Audience {output.audience ?? "General"}</span><span>{output.max_words == null ? "No word limit" : `${output.max_words} words`}</span><span>Config {output.render_config_hash ? output.render_config_hash.slice(0, 8) : "unavailable"}</span></div>{output.sections.map((section, index) => <section key={`${section.heading}-${index}`} className="brief-section"><p className="brief-index">{String(index + 1).padStart(2, "0")}</p><div><h3>{section.heading}</h3><p>{section.text}</p><div className="source-list" aria-label={`${section.heading} sources`}>{section.source_segment_ids.map((segmentId) => <span key={segmentId} className="source-reference">Source {segmentId}</span>)}{section.source_slot_ids.map((slotId) => <span key={slotId} className="source-reference">Slot {slotId}</span>)}</div></div></section>)}</article>) : <div className="empty-output" role="status"><p className="eyebrow">NO RENDERED OUTPUT</p><p>분석 진단은 준비되었습니다. 아직 생성된 검토용 출력은 없습니다.</p></div>}
        {activeOutput && <DiffView documentId={documentId} outputType={activeOutput.output_type} />}
      </section>
      <aside className="evidence-ledger" aria-labelledby="evidence-title"><div><p className="eyebrow">EVIDENCE LEDGER</p><h2 id="evidence-title">의미 단위 근거</h2></div><ul className="slot-list">{semanticMap.slots.map((slot) => <li key={slot.id}><b>{slot.slot}</b><span>{slot.text}</span>{slot.provenance?.source_segment_id && <span className="source-reference">Source {slot.provenance.source_segment_id}</span>}</li>)}</ul></aside>
    </div>
  </main>;
}
