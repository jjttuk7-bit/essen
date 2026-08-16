import { Identity } from "@/lib/api";

const KIND_HINTS: Record<string, string> = {
  "절차 안내서": "무엇을 어떤 순서로 할지 알려주는 문서",
  "분석 보고서": "수치로 상황을 진단하는 문서",
  "질문지": "답해야 할 질문을 모아둔 문서",
  "일반 문서": "",
};

/** What the reader is holding, before what it says. */
export function DocumentIdentity({ identity }: { identity: Identity }) {
  const hint = KIND_HINTS[identity.kind] ?? "";
  return <section className="identity" aria-labelledby="identity-title">
    <h2 id="identity-title">이 문서는</h2>
    <p className="identity-kind">
      <b>{identity.kind}</b>
      {hint && <span className="identity-hint">{hint}</span>}
    </p>
    <p className="identity-scale">
      {identity.section_count > 0 && <>{identity.section_count}개 절 · </>}
      {identity.segment_count}개 문단 · {identity.character_count.toLocaleString()}자
    </p>
    {identity.purpose && <blockquote className="identity-purpose">{identity.purpose}</blockquote>}
  </section>;
}
