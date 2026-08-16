import { UploadForm } from "@/frontend/components/upload-form";

const capabilities = [
  ["01", "원문 근거 추적", "모든 판단을 문서의 원문 근거와 함께 확인합니다."],
  ["02", "결정 공백 진단", "빠진 정보와 검증이 필요한 주장을 먼저 드러냅니다."],
  ["03", "실행 가능한 출력", "읽기 쉬운 요약과 다음 행동을 하나의 결과물로 만듭니다."],
];

export default function Home() {
  return (
    <main className="home-shell">
      <a className="skip-link" href="#upload">문서 업로드로 건너뛰기</a>
      <header className="masthead">
        <p className="wordmark">HUMAN <i>LAYER</i></p>
        <p className="edition">문서 근거를 <span>결정으로</span></p>
      </header>
      <section className="hero" aria-labelledby="page-title">
        <p className="eyebrow">DOCUMENT ANALYSIS WORKBENCH</p>
        <h1 id="page-title">문서 분석</h1>
        <p className="hero-copy">긴 문서에서 판단에 필요한 신호, 근거, 그리고 빠진 정보를 정리합니다.</p>
      </section>
      <section id="upload" className="upload-panel" aria-labelledby="upload-title">
        <div className="panel-head"><p>새 분석</p><h2 id="upload-title">분석할 문서를 선택하세요</h2></div>
        <UploadForm />
      </section>
      <aside className="principles" aria-label="Human Layer 분석 기능">
        {capabilities.map(([number, title, description]) => (
          <p key={number}><b>{number} · {title}</b>{description}</p>
        ))}
      </aside>
    </main>
  );
}
