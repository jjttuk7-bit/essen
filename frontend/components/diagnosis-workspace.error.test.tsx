import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

const { getOutputs, getDiff } = vi.hoisted(() => ({ getOutputs: vi.fn(), getDiff: vi.fn() }));
vi.mock("@/lib/api", () => ({ getOutputs, getDiff }));

import { DiagnosisWorkspace } from "./diagnosis-workspace";

afterEach(() => { cleanup(); vi.clearAllMocks(); });

describe("DiagnosisWorkspace failures", () => {
  it("keeps an accessible loading status while the document is pending", () => {
    getOutputs.mockReturnValue(new Promise(() => {}));
    getDiff.mockReturnValue(new Promise(() => {}));

    render(<DiagnosisWorkspace documentId="doc-1" />);

    expect(screen.getByText(/정리하는 중/)).toHaveAttribute("aria-live", "polite");
  });

  it.each(["Document not found", "Document has no completed analysis"])("shows a request error: %s", async (message) => {
    getOutputs.mockRejectedValue(new Error(message));
    getDiff.mockRejectedValue(new Error(message));

    render(<DiagnosisWorkspace documentId="doc-1" />);

    expect(await screen.findByRole("alert")).toHaveTextContent(message);
  });

  it("says so plainly when nothing was rendered", async () => {
    getOutputs.mockResolvedValue({ document_id: "doc-1", analysis_run_id: "run-1", outputs: [] });
    getDiff.mockRejectedValue(new Error("no output"));

    render(<DiagnosisWorkspace documentId="doc-1" />);

    expect(await screen.findByRole("status")).toHaveTextContent("정리된 문서가 아직 없습니다.");
  });

  it("still shows the document when the rationale cannot be loaded", async () => {
    getOutputs.mockResolvedValue({
      document_id: "doc-1", analysis_run_id: "run-1", outputs: [
        { id: "out-clean", output_type: "clean_version", content: "", version: 1, audience: null, max_words: null, render_config_hash: "h", sections: [{ heading: "Decision", text: "Launch the pilot.", source_slot_ids: ["s1"], source_segment_ids: ["S-01"] }] },
      ],
    });
    getDiff.mockRejectedValue(new Error("diff unavailable"));

    render(<DiagnosisWorkspace documentId="doc-1" />);

    expect(await screen.findByText("Launch the pilot.")).toBeVisible();
    expect(screen.queryByRole("alert")).toBeNull();
  });
});
