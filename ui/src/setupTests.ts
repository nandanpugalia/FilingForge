import "@testing-library/jest-dom";

// jsdom doesn't implement scrollIntoView (used by the dropdown to keep the active row visible).
if (!Element.prototype.scrollIntoView) {
  Element.prototype.scrollIntoView = () => {};
}
