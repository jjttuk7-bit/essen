import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

const { getDiagnosis, getSemanticMap, getOutputs } = vi.hoisted(() => ({ getDiagnosis: vi.fn(), getSemanticMap: vi.fn(), getOutputs: vi.fn() }));
vi.mock("@/lib/api", () => ({ getDiagnosis, getSemanticMap, getOutputs }));
import { DiagnosisWorkspace } from "./diagnosis-workspace";

afterEach(() => { cleanup(); vi.clearAllMocks(); });

describe("DiagnosisWorkspace failures", () => {
  it("keeps an accessible loading status while results are pending", () => {
    getDiagnosis.mockReturnValue(new Promise(() => {}));
    getSemanticMap.mockReturnValue(new Promise(() => {}));
    getOutputs.mockReturnValue(new Promise(() => {}));
    render(<DiagnosisWorkspace documentId="doc-1" />);
    expect(screen.getByText(/불러오는 중/)).toHaveAttribute("aria-live", "polite");
  });

  it.each(["Document not found", "Document has no completed analysis", "Semantic map unavailable", "Outputs unavailable"])("shows a request error: %s", async (message) => {
    getDiagnosis.mockRejectedValue(new Error(message));
    getSemanticMap.mockRejectedValue(new Error(message));
    getOutputs.mockRejectedValue(new Error(message));
    render(<DiagnosisWorkspace documentId="doc-1" />);
    expect(await screen.findByRole("alert")).toHaveTextContent(message);
  });
});

  it("keeps the diagnosis visible when no rendered outputs exist", async () => {
    getDiagnosis.mockResolvedValue({ document_signal_score: 72, signal_ratio: 0.68, redundancy_ratio: 0.2, evidence_coverage: 0.75, decision_completeness: 0.5, gaps: ["OWNER"] });
    getSemanticMap.mockResolvedValue({ slots: [{ id: "s1", slot: "FACT", text: "Revenue grew 20%." }] });
    getOutputs.mockResolvedValue({ document_id: "doc-1", analysis_run_id: "run-1", outputs: [] });

    render(<DiagnosisWorkspace documentId="doc-1" />);

    expect(await screen.findByText("72")).toBeVisible();
    expect(screen.getByRole("status")).toHaveTextContent("아직 생성된 검토용 출력은 없습니다.");
    expect(screen.getByText("Revenue grew 20%.")).toBeVisible();
  });

  it("shows an alert when only the output request fails", async () => {
    getDiagnosis.mockResolvedValue({ document_signal_score: 72, signal_ratio: 0.68, redundancy_ratio: 0.2, evidence_coverage: 0.75, decision_completeness: 0.5, gaps: [] });
    getSemanticMap.mockResolvedValue({ slots: [] });
    getOutputs.mockRejectedValue(new Error("Outputs unavailable"));

    render(<DiagnosisWorkspace documentId="doc-1" />);

    expect(await screen.findByRole("alert")).toHaveTextContent("Outputs unavailable");
  });
