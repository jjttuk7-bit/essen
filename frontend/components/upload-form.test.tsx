import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

const { routerPush, uploadDocument, analyzeDocument, renderDocument } = vi.hoisted(() => ({ routerPush: vi.fn(), uploadDocument: vi.fn(), analyzeDocument: vi.fn(), renderDocument: vi.fn() }));
vi.mock("next/navigation", () => ({ useRouter: () => ({ push: routerPush }) }));
vi.mock("@/lib/api", () => ({ uploadDocument, analyzeDocument, renderDocument }));
import { UploadForm } from "./upload-form";
afterEach(() => { cleanup(); vi.clearAllMocks(); });

function selectTextFile() { fireEvent.change(screen.getByLabelText(/분석할 문서/i), { target: { files: [new File(["brief"], "brief.txt", { type: "text/plain" })] } }); }

describe("UploadForm", () => {
  it("offers a labeled document picker and an analysis action", () => { render(<UploadForm />); expect(screen.getByLabelText(/분석할 문서/i)).toHaveAttribute("accept", ".txt,.md,.markdown,.pdf,.docx,.hwp,.hwpx"); expect(screen.getByRole("button", { name: /analyze document/i })).toBeVisible(); });
  it("uploads, analyzes, renders, then navigates to the result workspace", async () => {
    uploadDocument.mockResolvedValue({ document_id: "doc-1" }); analyzeDocument.mockResolvedValue({}); renderDocument.mockResolvedValue({}); render(<UploadForm />); selectTextFile(); fireEvent.click(screen.getByRole("button", { name: /analyze document/i }));
    expect(await screen.findByText("검토용 출력을 생성하고 있습니다…")).toHaveAttribute("aria-live", "polite");
    await waitFor(() => expect(renderDocument).toHaveBeenCalledWith("doc-1"));
    expect(analyzeDocument.mock.invocationCallOrder[0]).toBeLessThan(renderDocument.mock.invocationCallOrder[0]);
    expect(renderDocument.mock.invocationCallOrder[0]).toBeLessThan(routerPush.mock.invocationCallOrder[0]);
    expect(routerPush).toHaveBeenCalledWith("/documents/doc-1");
  });
  it("reports an API error to the user", async () => { uploadDocument.mockRejectedValue(new Error("Upload exceeds the 10 MB size limit")); render(<UploadForm />); selectTextFile(); fireEvent.click(screen.getByRole("button", { name: /analyze document/i })); expect(await screen.findByRole("alert")).toHaveTextContent("10 MB"); });
  it("reports a render error with the existing form alert", async () => { uploadDocument.mockResolvedValue({ document_id: "doc-1" }); analyzeDocument.mockResolvedValue({}); renderDocument.mockRejectedValue(new Error("Render unavailable")); render(<UploadForm />); selectTextFile(); fireEvent.click(screen.getByRole("button", { name: /analyze document/i })); expect(await screen.findByRole("alert")).toHaveTextContent("Render unavailable"); });
  it("keeps the analysis action named and announces upload progress", () => { uploadDocument.mockReturnValue(new Promise(() => {})); render(<UploadForm />); selectTextFile(); fireEvent.click(screen.getByRole("button", { name: /analyze document/i })); expect(screen.getByRole("button", { name: /analyze document/i })).toBeDisabled(); expect(screen.getByRole("button", { name: /analyze document/i })).toHaveAttribute("aria-busy", "true"); expect(screen.getByText("문서를 업로드하고 있습니다…")).toHaveAttribute("aria-live", "polite"); });
  it("shows the selected file and announces the upload stage", () => { uploadDocument.mockReturnValue(new Promise(() => {})); render(<UploadForm />); selectTextFile(); const selectedFile = screen.getByLabelText("Selected file"); expect(selectedFile).toHaveTextContent("brief.txt"); expect(selectedFile).toHaveTextContent("0.0 MB"); fireEvent.submit(screen.getByRole("button", { name: /analyze document/i }).closest("form")!); expect(screen.getByText("문서를 업로드하고 있습니다…")).toHaveAttribute("aria-live", "polite"); });
  it("ignores a second submit while the first request is pending", () => { uploadDocument.mockReturnValue(new Promise(() => {})); render(<UploadForm />); selectTextFile(); const form = screen.getByRole("button", { name: /analyze document/i }).closest("form")!; fireEvent.submit(form); fireEvent.submit(form); expect(uploadDocument).toHaveBeenCalledTimes(1); });
});
