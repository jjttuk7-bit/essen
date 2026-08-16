import { UploadForm } from "@/frontend/components/upload-form";

export default function Home() {
  return (
    <main className="home-shell">
      <a className="skip-link" href="#upload">문서 업로드로 건너뛰기</a>
      <header className="masthead">
        <p className="wordmark">HUMAN <i>LAYER</i></p>
        <p className="edition">Decision desk <span>01</span></p>
      </header>
      <section className="hero" aria-labelledby="page-title">
        <p className="eyebrow">DOCUMENT INTELLIGENCE / 2026</p>
        <h1 id="page-title">이 문서에서<br /><em>실제로 읽어야 할</em><br />내용은 얼마나 될까요?</h1>
        <p className="hero-copy">긴 문서를 판단과 실행이 가능한 정보로 다시 엮습니다. 모든 결론은 원문 근거까지 추적할 수 있습니다.</p>
      </section>
      <section id="upload" className="upload-panel" aria-labelledby="upload-title">
        <div className="panel-head"><p>01 / INPUT</p><h2 id="upload-title">문서를 올려주세요</h2></div>
        <UploadForm />
      </section>
      <aside className="principles" aria-label="How Human Layer works">
        <p><b>01</b> 핵심 신호와 반복을 분리합니다.</p>
        <p><b>02</b> 근거 없는 주장과 누락을 찾습니다.</p>
        <p><b>03</b> 결정과 실행에 맞는 출력으로 재구성합니다.</p>
      </aside>
    </main>
  );
}
