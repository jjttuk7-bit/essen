import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

const { routerPush, uploadDocument, analyzeDocument } = vi.hoisted(() => ({ routerPush: vi.fn(), uploadDocument: vi.fn(), analyzeDocument: vi.fn() }));
vi.mock("next/navigation", () => ({ useRouter: () => ({ push: routerPush }) }));
vi.mock("@/lib/api", () => ({ uploadDocument, analyzeDocument }));
import { UploadForm } from "./upload-form";
afterEach(() => { cleanup(); vi.clearAllMocks(); });

function selectTextFile() { fireEvent.change(screen.getByLabelText(/분석할 문서/i), { target: { files: [new File(["brief"], "brief.txt", { type: "text/plain" })] } }); }

describe("UploadForm", () => {
  it("offers a labeled document picker and an analysis action", () => { render(<UploadForm />); expect(screen.getByLabelText(/분석할 문서/i)).toHaveAttribute("accept", ".txt,.md,.markdown,.pdf"); expect(screen.getByRole("button", { name: /analyze document/i })).toBeVisible(); });
  it("uploads, analyzes, then navigates to the result workspace", async () => { uploadDocument.mockResolvedValue({ document_id: "doc-1" }); analyzeDocument.mockResolvedValue({}); render(<UploadForm />); selectTextFile(); fireEvent.click(screen.getByRole("button", { name: /analyze document/i })); await waitFor(() => expect(analyzeDocument).toHaveBeenCalledWith("doc-1")); expect(routerPush).toHaveBeenCalledWith("/documents/doc-1"); });
  it("reports an API error to the user", async () => { uploadDocument.mockRejectedValue(new Error("Upload exceeds the 10 MB size limit")); render(<UploadForm />); selectTextFile(); fireEvent.click(screen.getByRole("button", { name: /analyze document/i })); expect(await screen.findByRole("alert")).toHaveTextContent("10 MB"); });
  it("ignores a second submit while the first request is pending", () => { uploadDocument.mockReturnValue(new Promise(() => {})); render(<UploadForm />); selectTextFile(); const form = screen.getByRole("button", { name: /analyze document/i }).closest("form")!; fireEvent.submit(form); fireEvent.submit(form); expect(uploadDocument).toHaveBeenCalledTimes(1); });
});