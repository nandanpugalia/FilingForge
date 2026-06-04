import { it, expect } from "vitest";
import { CATEGORIES } from "../categories";
// Mirror of engine/models.py CURATED_BY_KEY keys — keep in sync (see engine CURATED).
const ENGINE_KEYS = ["annual_report","results","investor_ppt","concall","board_outcome","press","analyst_meet","corp_actions","agm_egm"];
it("UI category keys exactly match the engine's curated keys", () => {
  expect(CATEGORIES.map(c => c.key)).toEqual(ENGINE_KEYS);
});
