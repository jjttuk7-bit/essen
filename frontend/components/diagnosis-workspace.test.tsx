import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

vi.mock("@/lib/api", () => ({
  getDiagnosis: vi.fn().mockResolvedValue({ document_signal_score: 72, signal_ratio: 0.68, redundancy_ratio: 0.2, evidence_coverage: 0.75, decision_completeness: 0.5, purpose: "DECIDE", audience: "leaders", gaps: ["OWNER"] }),
  getSemanticMap: vi.fn().mockResolvedValue({ slots: [{ id: "s1", slot: "FACT", text: "Revenue grew 20%.", provenance: { source_segment_id: "S-01" } }] }),
  getOutputs: vi.fn().mockResolvedValue({
    document_id: "doc-1", analysis_run_id: "run-1", outputs: [
      { id: "out-clean", output_type: "clean_version", content: "", version: 1, audience: null, max_words: null, render_config_hash: "hash", sections: [{ heading: "Clean brief", text: "The clean analysis text.", source_slot_ids: ["s1"], source_segment_ids: ["S-03"] }] },
      { id: "out-exec", output_type: "executive_summary", content: "", version: 1, audience: null, max_words: null, render_config_hash: "hash", sections: [{ heading: "Executive brief", text: "The executive analysis text.", source_slot_ids: [], source_segment_ids: ["S-05"] }] },
      { id: "out-action", output_type: "action_decision_sheet", content: "", version: 1, audience: null, max_words: null, render_config_hash: "hash", sections: [{ heading: "Action plan", text: "The action output text.", source_slot_ids: [], source_segment_ids: ["S-09"] }] },
    ],
  }),
}));

import { DiagnosisWorkspace } from "./diagnosis-workspace";

afterEach(() => cleanup());

describe("DiagnosisWorkspace", () => {
  it("shows the document score and extracted semantic evidence", async () => {
    render(<DiagnosisWorkspace documentId="doc-1" />);
    expect(await screen.findByText("72")).toBeVisible();
    expect(screen.getByText("Revenue grew 20%.")).toBeVisible();
    expect(screen.getByText("Source S-01")).toBeVisible();
    expect(screen.getByText("OWNER")).toBeVisible();
  });

  it("maps backend output types to clear labels and switches the active mode", async () => {
    render(<DiagnosisWorkspace documentId="doc-1" />);
    expect(await screen.findByRole("tablist", { name: /output mode/i })).toBeVisible();
    expect(screen.getByRole("tab", { name: "Clean brief" })).toHaveAttribute("aria-selected", "true");
    expect(screen.getByText("The clean analysis text.")).toBeVisible();
    expect(screen.getByText("Source S-03")).toBeVisible();

    fireEvent.click(screen.getByRole("tab", { name: "Action plan" }));

    expect(screen.getByRole("tab", { name: "Action plan" })).toHaveAttribute("aria-selected", "true");
    expect(screen.getByText("The action output text.")).toBeVisible();
  });

  it("changes the active output with ArrowRight", async () => {
    render(<DiagnosisWorkspace documentId="doc-1" />);
    const cleanTab = await screen.findByRole("tab", { name: "Clean brief" });
    cleanTab.focus();

    fireEvent.keyDown(cleanTab, { key: "ArrowRight" });

    expect(screen.getByRole("tab", { name: "Executive brief" })).toHaveAttribute("aria-selected", "true");
    expect(screen.getByRole("tab", { name: "Executive brief" })).toHaveFocus();
  });
});
