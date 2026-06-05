import { it, expect } from "vitest";
import { tickerFor } from "../lib/ticker";
it("uses the BSE symbol when present", () => {
  expect(tickerFor({ scrip_code: "532540", company: "Tata Consultancy Services Ltd", is_primary: true, symbol: "TCS" })).toBe("TCS");
});
it("falls back to first word when symbol absent", () => {
  expect(tickerFor({ scrip_code: "1", company: "Reliance Industries Ltd", is_primary: true })).toBe("RELIANCE");
});
