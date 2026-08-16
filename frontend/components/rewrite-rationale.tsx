"use client";

import { useState } from "react";
import { DiffResponse, Disposition } from "@/lib/api";

const labels: Record<Disposition, string> = { REMOVED: "삭제", MERGED: "통합", EMPHASIZED: "그대로", HELD: "제외" };
const order: Disposition[] = ["EMPHASIZED", "MERGED", "REMOVED", "HELD"];

function kept(diff: DiffResponse): number {
  return diff.counts.EMPHASIZED + diff.counts.MERGED;
}

/** What this document cost the reader, and what was done about it. */
export function RewriteRationale({ diff }: { diff: DiffResponse }) {
  const [open, setOpen] = useState(false);

  const total = diff.entries.length;
  const share = total ? Math.round((kept(diff) / total) * 100) : 0;
  const grouped = order
    .map((disposition) => ({ disposition, entries: diff.entries.filter((entry) => entry.disposition === disposition) }))
    .filter((group) => group.entries.length > 0);

  return <section className="rationale" aria-labelledby="rationale-title">
    <h2 id="rationale-title">이 문서의 병목</h2>

    {diff.bottlenecks.length > 0
      ? <ul className="bottleneck-list">
          {diff.bottlenecks.map((finding) => <li key={finding.kind}>
            <p className="bottleneck-head"><b>{finding.label}</b><span>{Math.round(finding.share * 100)}%</span></p>
            <p className="bottleneck-detail">{finding.detail}</p>
          </li>)}
        </ul>
      : <p className="rationale-summary">읽는 시간을 뺏는 구간은 발견되지 않았습니다.</p>}

    <p className="rationale-summary">원문 {total}개 문단 중 {kept(diff)}개를 남겼습니다. 원문의 {share}%입니다.</p>

    <button type="button" className="rationale-toggle" aria-expanded={open} onClick={() => setOpen(!open)}>
      {open ? "근거 접기" : "문단별 근거 보기"}
    </button>
    {open && <ul className="rationale-list">
      {grouped.map(({ disposition, entries }) => <li key={disposition}>
        <p className="rationale-group"><b className={`diff-badge diff-${disposition.toLowerCase()}`}>{labels[disposition]}</b>{entries.length}개 문단</p>
        <ul className="rationale-reasons">
          {entries.map((entry) => <li key={entry.segment_id}>
            <span className="rationale-quote">{entry.original_text.slice(0, 90)}{entry.original_text.length > 90 ? "…" : ""}</span>
            <span className="rationale-why">{entry.reason}</span>
          </li>)}
        </ul>
      </li>)}
    </ul>}
  </section>;
}
