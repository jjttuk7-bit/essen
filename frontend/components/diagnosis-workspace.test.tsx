import { cleanup, fireEvent, render, screen, within } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

const { getOutputs, getDiff } = vi.hoisted(() => ({ getOutputs: vi.fn(), getDiff: vi.fn() }));
vi.mock("@/lib/api", () => ({ getOutputs, getDiff }));

import { DiagnosisWorkspace } from "./diagnosis-workspace";

const outputs = {
  document_id: "doc-1", analysis_run_id: "run-1", outputs: [
    { id: "out-clean", output_type: "clean_version", content: "", version: 2, audience: null, max_words: null, render_config_hash: "hash", sections: [
      { heading: "Decision", text: "Launch the pilot in Q3.\nKim owns delivery.", source_slot_ids: ["s1", "s2"], source_segment_ids: ["S-01", "S-02"] },
    ] },
    { id: "out-action", output_type: "action_decision_sheet", content: "", version: 1, audience: null, max_words: null, render_config_hash: "hash", sections: [
      { heading: "Actions", text: "Deploy by Friday.", source_slot_ids: ["s3"], source_segment_ids: ["S-03"] },
    ] },
  ],
};

const diff = {
  document_id: "doc-1", analysis_run_id: "run-1", output_id: "out-clean", output_type: "clean_version", output_version: 2,
  counts: { REMOVED: 1, MERGED: 1, EMPHASIZED: 1, HELD: 1 },
  entries: [
    { segment_id: "S-01", order_index: 0, original_text: "Decision: launch the pilot.", disposition: "EMPHASIZED", reason: "Carried into the output as its own section under 'Decision'.", rendered_headings: ["Decision"], provenance: { source_segment_id: "S-01" } },
    { segment_id: "S-02", order_index: 1, original_text: "Kim owns delivery.", disposition: "MERGED", reason: "Combined with 1 other source segment under 'Decision'.", rendered_headings: ["Decision"], provenance: { source_segment_id: "S-02" } },
    { segment_id: "S-03", order_index: 2, original_text: "As we all know, quality matters.", disposition: "REMOVED", reason: "States a general truth without document-specific content.", rendered_headings: [], provenance: { source_segment_id: "S-03" } },
    { segment_id: "S-04", order_index: 3, original_text: "Table of contents.", disposition: "HELD", reason: "No semantic content was extracted from this segment.", rendered_headings: [], provenance: { source_segment_id: "S-04" } },
  ],
};

afterEach(() => { cleanup(); vi.clearAllMocks(); });

describe("DiagnosisWorkspace", () => {
  it("presents the rewritten document as discrete items rather than one paragraph", async () => {
    getOutputs.mockResolvedValue(outputs);
    getDiff.mockResolvedValue(diff);

    render(<DiagnosisWorkspace documentId="doc-1" />);

    const items = await screen.findAllByRole("listitem");
    expect(items[0]).toHaveTextContent("Launch the pilot in Q3.");
    expect(items[1]).toHaveTextContent("Kim owns delivery.");
  });

  it("does not show analysis machinery on the document page", async () => {
    getOutputs.mockResolvedValue(outputs);
    getDiff.mockResolvedValue(diff);

    render(<DiagnosisWorkspace documentId="doc-1" />);
    await screen.findByText("Launch the pilot in Q3.");

    expect(screen.queryByText(/Source S-01/)).toBeNull();
    expect(screen.queryByText(/Slot s1/)).toBeNull();
    expect(screen.queryByText(/EVIDENCE LEDGER/i)).toBeNull();
    expect(screen.queryByText(/Config/)).toBeNull();
  });

  it("switches between the document forms", async () => {
    getOutputs.mockResolvedValue(outputs);
    getDiff.mockResolvedValue(diff);

    render(<DiagnosisWorkspace documentId="doc-1" />);
    expect(await screen.findByRole("tab", { name: "정리본" })).toHaveAttribute("aria-selected", "true");

    fireEvent.click(screen.getByRole("tab", { name: "실행안" }));

    expect(screen.getByText("Deploy by Friday.")).toBeVisible();
    expect(getDiff).toHaveBeenCalledWith("doc-1", "action_decision_sheet");
  });

  it("gives one reason the document was rewritten, with details on request", async () => {
    getOutputs.mockResolvedValue(outputs);
    getDiff.mockResolvedValue(diff);

    render(<DiagnosisWorkspace documentId="doc-1" />);
    const rationale = await screen.findByRole("region", { name: "이 문서를 다시 만든 이유" });

    expect(rationale).toHaveTextContent("원문 4개 문단 중 2개를 남기고 2개를 덜어냈습니다. 원문의 50%입니다.");
    expect(within(rationale).queryByText(/States a general truth/)).toBeNull();

    fireEvent.click(within(rationale).getByRole("button", { name: /근거 보기/ }));

    expect(within(rationale).getByText(/States a general truth/)).toBeVisible();
  });
});
