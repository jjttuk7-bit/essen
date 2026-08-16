import { describe, expect, it } from "vitest";
import { apiBaseUrlFor } from "./api";
describe("apiBaseUrlFor", () => {
  it("uses the local API only for local development", () => { expect(apiBaseUrlFor("development", undefined)).toBe("http://127.0.0.1:8000"); });
  it("does not substitute a local API URL for production", () => { expect(apiBaseUrlFor("production", undefined)).toBe(""); });
});