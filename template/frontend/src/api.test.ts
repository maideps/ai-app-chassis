import { describe, expect, it, vi } from "vitest";
import { ApiError, api } from "./api";

describe("api", () => {
  it("prefixes /api and sends the text as JSON", async () => {
    const fetchMock = vi
      .spyOn(globalThis, "fetch")
      .mockResolvedValue(new Response(JSON.stringify({ summary: "s", keywords: [] }), { status: 200 }));
    await expect(api.summarize("hello")).resolves.toEqual({ summary: "s", keywords: [] });
    expect(fetchMock).toHaveBeenCalledWith("/api/summarize", {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ text: "hello" }),
    });
  });

  it("turns a non-JSON error body into a generic ApiError", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(new Response("<html>bad gateway</html>", { status: 502 }));
    const error = await api.health().catch((err: unknown) => err);
    expect(error).toBeInstanceOf(ApiError);
    expect(error).toMatchObject({ status: 502, rule: null, message: "request failed (HTTP 502)" });
  });
});
