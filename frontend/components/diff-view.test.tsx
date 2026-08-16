import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

const getDiff = vi.fn();
vi.mock("@/lib/api", () => ({ getDiff: (...args: unknown[]) => getDiff(...args) }));

import { DiffView } from "./diff-view";

const diff = {
  document_id: "doc-1",
  analysis_run_id: "run-1",
  output_id: "out-clean",
  output_type: "clean_version",
  output_version: 2,
  counts: { REMOVED: 1, MERGED: 1, EMPHASIZED: 1, HELD: 1 },
  entries: [
    { segment_id: "S-01", order_index: 0, original_text: "Decision: launch the pilot.", disposition: "EMPHASIZED", reason: "Carried into the output as its own section under 'Decisions'.", rendered_headings: ["Decisions"], provenance: { source_segment_id: "S-01" } },
    { segment_id: "S-02", order_index: 1, original_text: "Kim owns delivery.", disposition: "MERGED", reason: "Combined with 1 other source segment under 'Owners'.", rendered_headings: ["Owners"], provenance: { source_segment_id: "S-02" } },
    { segment_id: "S-03", order_index: 2, original_text: "As we all know, quality matters.", disposition: "REMOVED", reason: "States a general truth without document-specific content.", rendered_headings: [], provenance: { source_segment_id: "S-03" } },
    { segment_id: "S-04", order_index: 3, original_text: "Background note.", disposition: "HELD", reason: "Extracted content was not selected for this output.", rendered_headings: [], provenance: { source_segment_id: "S-04" } },
  ],
};

afterEach(() => { cleanup(); getDiff.mockReset(); });

describe("DiffView", () => {
  it("shows every source segment with its disposition and reason", async () => {
    getDiff.mockResolvedValue(diff);
    render(<DiffView documentId="doc-1" outputType="clean_version" />);

    expect(await screen.findByText("Decision: launch the pilot.")).toBeVisible();
    expect(screen.getByText("As we all know, quality matters.")).toBeVisible();
    expect(screen.getByText("States a general truth without document-specific content.")).toBeVisible();
    expect(screen.getByText("Combined with 1 other source segment under 'Owners'.")).toBeVisible();
  });

  it("labels each disposition in Korean and counts them", async () => {
    getDiff.mockResolvedValue(diff);
    render(<DiffView documentId="doc-1" outputType="clean_version" />);

    expect(await screen.findByText("강조")).toBeVisible();
    expect(screen.getByText("통합")).toBeVisible();
    expect(screen.getByText("삭제")).toBeVisible();
    expect(screen.getByText("보류")).toBeVisible();
    expect(screen.getByRole("list", { name: /원문 대비 변경/i })).toBeVisible();
  });

  it("refetches when the active output type changes", async () => {
    getDiff.mockResolvedValue(diff);
    const { rerender } = render(<DiffView documentId="doc-1" outputType="clean_version" />);
    await screen.findByText("Decision: launch the pilot.");

    rerender(<DiffView documentId="doc-1" outputType="executive_summary" />);

    expect(getDiff).toHaveBeenCalledWith("doc-1", "executive_summary");
  });

  it("explains when the output has not been rendered yet", async () => {
    getDiff.mockRejectedValue(new Error("Render the clean_version output before requesting its diff"));
    render(<DiffView documentId="doc-1" outputType="clean_version" />);

    expect(await screen.findByRole("status")).toHaveTextContent(/before requesting its diff/i);
  });
});
