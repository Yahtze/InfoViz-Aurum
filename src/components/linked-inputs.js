// Keep Several Slider Inputs (One per Panel) on the Same Value, so Setting One Sets All
//
// Usage:
//   const linked = linkInputs();
//   linked.add(someRangeInput);   // Each Input Still Lives in its Own Panel's Toolbar
export function linkInputs() {
  const inputs = new Set();
  let syncing = false;

  function add(input) {
    inputs.add(input);
    input.addEventListener("input", () => {
      if (syncing) return;
      syncing = true;
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
