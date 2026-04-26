import { describe, expect, it } from "vitest";

import { isPushSupported } from "@/lib/webpush";

describe("webpush helpers", () => {
  it("detects push support based on platform APIs", () => {
    // jsdom doesn't ship PushManager; isPushSupported should return false.
    expect(isPushSupported()).toBe(false);
  });
});
