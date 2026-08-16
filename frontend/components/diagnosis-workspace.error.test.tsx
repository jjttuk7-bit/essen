import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

const { getDiagnosis, getSemanticMap } = vi.hoisted(() => ({ getDiagnosis: vi.fn(), getSemanticMap: vi.fn() }));
vi.mock("@/lib/api", () => ({ getDiagnosis, getSemanticMap }));
import { DiagnosisWorkspace } from "./diagnosis-workspace";

afterEach(() => { cleanup(); vi.clearAllMocks(); });

describe("DiagnosisWorkspace failures", () => {
  it("keeps an accessible loading status while results are pending", () => {
    getDiagnosis.mockReturnValue(new Promise(() => {}));
    getSemanticMap.mockReturnValue(new Promise(() => {}));
    render(<DiagnosisWorkspace documentId="doc-1" />);
    expect(screen.getByText(/불러오는 중/)).toHaveAttribute("aria-live", "polite");
  });

  it.each(["Document not found", "Document has no completed analysis", "Semantic map unavailable"])("shows a request error: %s", async (message) => {
    getDiagnosis.mockRejectedValue(new Error(message));
    getSemanticMap.mockRejectedValue(new Error(message));
    render(<DiagnosisWorkspace documentId="doc-1" />);
    expect(await screen.findByRole("alert")).toHaveTextContent(message);
  });
});
