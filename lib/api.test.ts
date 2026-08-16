import { afterEach, describe, expect, it, vi } from "vitest";
import * as api from "./api";

afterEach(() => vi.restoreAllMocks());

describe("apiBaseUrlFor", () => {
  it("uses the local API only for local development", () => { expect(api.apiBaseUrlFor("development", undefined)).toBe("http://127.0.0.1:8000"); });
  it("does not substitute a local API URL for production", () => { expect(api.apiBaseUrlFor("production", undefined)).toBe(""); });
});

describe("getOutputs", () => {
  it("gets persisted outputs with section source slot and segment IDs", async () => {
    const payload = { document_id: "doc-1", analysis_run_id: "run-1", outputs: [{ id: "output-1", output_type: "executive_summary", content: "Decision summary", sections: [{ heading: "Decision", text: "Approve", source_slot_ids: ["slot-1"], source_segment_ids: ["segment-1"] }], version: 1, audience: "CEO", max_words: 120, render_config_hash: "config-1" }] };
    const fetchMock = vi.fn().mockResolvedValue({ ok: true, json: async () => payload });
    vi.stubGlobal("fetch", fetchMock);

    const response = await api.getOutputs("doc-1");

    expect(fetchMock).toHaveBeenCalledWith(expect.stringMatching(/\/documents\/doc-1\/outputs$/), { method: "GET" });
    expect(response.outputs[0].sections[0].source_slot_ids).toEqual(["slot-1"]);
    expect(response.outputs[0].sections[0].source_segment_ids).toEqual(["segment-1"]);
  });
});

describe("renderDocument", () => {
  it("posts to the persisted output render endpoint", async () => {
    const fetchMock = vi.fn().mockResolvedValue({ ok: true, json: async () => ({ outputs: [] }) });
    vi.stubGlobal("fetch", fetchMock);

    await api.renderDocument("doc-1");

    expect(fetchMock).toHaveBeenCalledWith(expect.stringMatching(/\/documents\/doc-1\/render$/), { method: "POST" });
  });
});
