"use client";

import { useEffect, useState } from "react";
import { DiffResponse, Disposition, getDiff } from "@/lib/api";

const dispositionLabels: Record<Disposition, string> = { REMOVED: "삭제", MERGED: "통합", EMPHASIZED: "강조", HELD: "보류" };
const dispositionOrder: Disposition[] = ["EMPHASIZED", "MERGED", "REMOVED", "HELD"];

export function DiffView({ documentId, outputType }: { documentId: string; outputType: string }) {
  const [diff, setDiff] = useState<DiffResponse | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    setDiff(null); setNotice(null);
    getDiff(documentId, outputType)
      .then((next) => { if (active) setDiff(next); })
      .catch((cause) => { if (active) setNotice(cause instanceof Error ? cause.message : "변경 내역을 불러오지 못했습니다."); });
    return () => { active = false; };
  }, [documentId, outputType]);

  if (notice) return <section className="diff-panel"><p role="status">{notice}</p></section>;
  if (!diff) return <section className="diff-panel"><p aria-live="polite">원문 대비 변경 내역을 불러오는 중…</p></section>;

  return <section className="diff-panel" aria-labelledby="diff-title">
    <div className="workspace-title-row">
      <div><p className="eyebrow">SOURCE DIFF</p><h2 id="diff-title">원문 대비 변경</h2></div>
      <div className="diff-counts">{dispositionOrder.map((disposition) => <span key={disposition} className={`diff-count diff-${disposition.toLowerCase()}`}>{dispositionLabels[disposition]} {diff.counts[disposition] ?? 0}</span>)}</div>
    </div>
    <ul className="diff-list" aria-label="원문 대비 변경 내역">
      {diff.entries.map((entry) => <li key={entry.segment_id} className={`diff-entry diff-${entry.disposition.toLowerCase()}`}>
        <p className="brief-index">{String(entry.order_index + 1).padStart(2, "0")}</p>
        <div>
          <p className="diff-original">{entry.original_text}</p>
          <p className="diff-reason"><b className="diff-badge">{dispositionLabels[entry.disposition]}</b>{entry.reason}</p>
          <div className="source-list" aria-label={`Segment ${entry.segment_id} sources`}>
            <span className="source-reference">Source {entry.provenance.source_segment_id}</span>
            {entry.rendered_headings.map((heading) => <span key={heading} className="source-reference">→ {heading}</span>)}
          </div>
        </div>
      </li>)}
    </ul>
  </section>;
}
