// Reusable Full Screen Panel: Holds a Chart and its Controls so Both Stay Interactive in Full Screen
//
// Usage (Create the Panel in its Own Cell so it is not Rebuilt when a Control Changes):
//   const panel = fullscreenPanel();
//   display(panel.element);
//   panel.addControl(someInputOrButton);   // Shown in the Toolbar, also in Full Screen
//   panel.setChart(svg.node());            // Replaces the Chart Without Leaving Full Screen
export function fullscreenPanel() {
  const element = document.createElement("div");
  element.className = "fullscreen-panel";

  const toolbar = document.createElement("div");
  toolbar.className = "fullscreen-toolbar";

  const controls = document.createElement("div");
  controls.className = "fullscreen-controls";

  const button = document.createElement("button");
  button.className = "fullscreen-button";
  button.type = "button";

  const content = document.createElement("div");
  content.className = "fullscreen-content";

  toolbar.append(controls, button);
  element.append(toolbar, content);

  // Hide the Button where the Browser Cannot Full Screen an Arbitrary Element
  const supported = typeof element.requestFullscreen === "function";
  if (!supported) button.hidden = true;

  const isFullscreen = () => document.fullscreenElement === element;

  const sync = () => {
    const on = isFullscreen();
    element.classList.toggle("is-fullscreen", on);
    button.textContent = on ? "✕ Exit Full Screen" : "⛶ Full Screen";
    button.setAttribute("aria-pressed", String(on));
  };

  button.onclick = () => {
    const request = isFullscreen() ? document.exitFullscreen() : element.requestFullscreen();
    request.catch(() => {});
  };

  element.addEventListener("fullscreenchange", sync);
  sync();

  return {
    element,
    addControl: (node) => controls.append(node),
    setChart: (node) => {
      // Record the Chart's Aspect Ratio (from its viewBox) so Full Screen can Size it to Fit
      const box = node.viewBox?.baseVal;
      if (box?.width && box?.height) node.style.setProperty("--ratio", box.width / box.height);
      content.replaceChildren(node);
    }
  };
}
