"use client";

import { useEffect, useState } from "react";
import { DiffResponse, Disposition, getDiff } from "@/lib/api";

const labels: Record<Disposition, string> = { REMOVED: "삭제", MERGED: "통합", EMPHASIZED: "그대로", HELD: "제외" };
const order: Disposition[] = ["EMPHASIZED", "MERGED", "REMOVED", "HELD"];

function summarize(diff: DiffResponse): string {
  const kept = diff.counts.EMPHASIZED + diff.counts.MERGED;
  const dropped = diff.counts.REMOVED + diff.counts.HELD;
  const share = diff.entries.length ? Math.round((kept / diff.entries.length) * 100) : 0;
  return `원문 ${diff.entries.length}개 문단 중 ${kept}개를 남기고 ${dropped}개를 덜어냈습니다. 원문의 ${share}%입니다.`;
}

/** The single "why" the reader gets: what was dropped, and on what grounds. */
export function RewriteRationale({ documentId, outputType }: { documentId: string; outputType: string }) {
  const [diff, setDiff] = useState<DiffResponse | null>(null);
  const [open, setOpen] = useState(false);

  useEffect(() => {
    let active = true;
    setDiff(null);
    getDiff(documentId, outputType).then((next) => { if (active) setDiff(next); }).catch(() => undefined);
    return () => { active = false; };
  }, [documentId, outputType]);

  if (!diff) return null;

  const grouped = order.map((disposition) => ({
    disposition,
    entries: diff.entries.filter((entry) => entry.disposition === disposition),
  })).filter((group) => group.entries.length > 0);

  return <section className="rationale" aria-labelledby="rationale-title">
    <h2 id="rationale-title">이 문서를 다시 만든 이유</h2>
    <p className="rationale-summary">{summarize(diff)}</p>
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
