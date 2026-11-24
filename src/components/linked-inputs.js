// Keep Several Slider Inputs (One per Panel) on the Same Value, so Setting One Sets All
// The Value is Remembered for the Browser Session, so the Other Pages Start from the Same Setting
//
// Usage:
//   const linked = linkInputs();
//   linked.add(someRangeInput);   // Each Input Still Lives in its Own Panel's Toolbar
const STORAGE_KEY = "aurum-country-count";

export function linkInputs() {
  const inputs = new Set();
  let syncing = false;

  // Chart Heights Follow the Count, so Redrawing Other Panels Above the Slider can Push it Out of View.
  // Scroll the Page by the Slider's Drift for a Moment After a Change to Keep it Under the Pointer.
  function holdPosition(input) {
    if (document.fullscreenElement) return;
    const top = input.getBoundingClientRect().top;
    let frames = 0;
    const settle = () => {
      const drift = input.getBoundingClientRect().top - top;
      if (Math.abs(drift) > 0.5) window.scrollBy(0, drift);
      if (++frames < 20) requestAnimationFrame(settle);
    };
    requestAnimationFrame(settle);
  }

  function add(input) {
    try {
      const saved = sessionStorage.getItem(STORAGE_KEY);
      const range = input.querySelector("input[type=range]");
      if (saved !== null && +saved >= +range.min && +saved <= +range.max) input.value = saved;
    } catch {}
    inputs.add(input);
    input.addEventListener("input", () => {
      if (syncing) return;
      syncing = true;
      try { sessionStorage.setItem(STORAGE_KEY, input.value); } catch {}
      holdPosition(input);
      for (const other of inputs) {
        if (!other.isConnected) inputs.delete(other); // Drop Inputs from Cells that were Re-Run
        else if (other !== input && other.value !== input.value) {
          other.value = input.value;
          other.dispatchEvent(new Event("input", {bubbles: true})); // Redraws that Panel's Chart
        }
      }
      syncing = false;
    });
    return input;
  }

  return {add};
}
