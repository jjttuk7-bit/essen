import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

vi.mock("@/lib/api", () => ({
  getDiagnosis: vi.fn().mockResolvedValue({
    document_signal_score: 72,
    signal_ratio: 0.68,
    redundancy_ratio: 0.2,
    evidence_coverage: 0.75,
    decision_completeness: 0.5,
    purpose: "DECIDE",
    audience: "leaders",
    gaps: ["OWNER"],
  }),
  getSemanticMap: vi.fn().mockResolvedValue({
    slots: [{ id: "s1", slot: "FACT", text: "Revenue grew 20%." }],
  }),
}));

import { DiagnosisWorkspace } from "./diagnosis-workspace";

describe("DiagnosisWorkspace", () => {
  it("shows the document score and extracted semantic evidence", async () => {
    render(<DiagnosisWorkspace documentId="doc-1" />);

    expect(await screen.findByText("72")).toBeVisible();
    expect(screen.getByText("Revenue grew 20%.")).toBeVisible();
    expect(screen.getByText("OWNER")).toBeVisible();
  });
});
