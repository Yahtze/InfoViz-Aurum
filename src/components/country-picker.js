// Reusable Country Picker: Search, Continent Filter, Sorting, Presets, and a Selection Remembered Across Pages
//
// Usage (Create it in its Own Cell, then Add it to a Panel's Toolbar):
//   const picker = countryPicker({names, continents, presets, sorts, detail, defaults, linked});
//   panel.addControl(picker);
//   const selected = Generators.input(picker);   // Array of the Selected Country Names
//
//   names:      Every Country that can be Selected
//   continents: Map from Country Name to Continent (Drives the Continent Filter)
//   presets:    [{label, pick: (n) => [Country Names]}]; Each Preset Button Selects the Top n by its Own Rule
//   sorts:      [{label, compare: (a, b) => Number}] Extra Ways to Order the List, after Name (A–Z)
//   detail:     Optional (name) => Text Shown Beside Each Name, such as its Value
//   defaults:   The Selection Used the First Time, before the Reader Has Chosen Anything
//   linked:     The Page's linkInputs() Instance, so the Preset Slider Matches the Other Sliders
//   fullScreenMax: Most Countries the Chart Draws in Full Screen, where More would be Unreadable
import * as d3 from "npm:d3";
import * as Inputs from "npm:@observablehq/inputs";

const STORAGE_KEY = "aurum-country-selection";

function readStored() {
  try {
    const saved = JSON.parse(sessionStorage.getItem(STORAGE_KEY));
    return Array.isArray(saved) ? saved : null;
  } catch {
    return null;
  }
}

export function countryPicker({names, continents, presets, sorts = [], detail = () => "", defaults, linked, fullScreenMax = 10}) {
  const nameSet = new Set(names);
  const allSorts = [{label: "Name (A–Z)", compare: (a, b) => d3.ascending(a, b)}, ...sorts];
  const continentNames = [...new Set(names.map((n) => continents.get(n)).filter(Boolean))].sort(d3.ascending);

  // Start from the Remembered Selection when it Includes Countries Available Here
  const stored = readStored();
  const remembered = stored?.filter((n) => nameSet.has(n)) ?? [];
  const selected = new Set(stored === null || (stored.length > 0 && remembered.length === 0) ? defaults : remembered);

  const filters = {search: "", continent: "All Continents", sort: 0};
  let presetIndex = null;

  // In Full Screen at Most fullScreenMax Countries can be Selected
  const isFullScreen = () => document.fullscreenElement?.contains(root) ?? false;

  // Build the Controls
  const root = document.createElement("div");
  root.className = "country-picker-ui";

  const makeButton = (label, onclick) => {
    const b = document.createElement("button");
    b.type = "button";
    b.className = "reset-button";
    b.textContent = label;
    b.onclick = onclick;
    return b;
  };

  // Row One: Presets, Clear, and the Slider for How Many Countries a Preset Selects (Only Shown while a Preset is Active)
  const presetRow = document.createElement("div");
  presetRow.className = "picker-row";

  const presetLabel = document.createElement("span");
  presetLabel.className = "picker-label";
  presetLabel.textContent = "Presets";
  presetRow.append(presetLabel);

  const presetButtons = presets.map((preset, i) => {
    const b = makeButton(preset.label, () => {
      presetIndex = i;
      applyPreset();
    });
    b.setAttribute("aria-pressed", "false");
    presetRow.append(b);
    return b;
  });

  presetRow.append(makeButton("Clear", () => {
    presetIndex = null;
    setSelection([]);
  }));

  const countInput = Inputs.range([3, 20], {label: "Countries per Preset", step: 1, value: 10});
  linked.add(countInput);
  countInput.hidden = true;
  countInput.addEventListener("input", () => { if (presetIndex !== null) applyPreset(); });
  presetRow.append(countInput);

  // Row Two: Search, Continent Filter, Sort, and Bulk Buttons for the Countries Currently Shown
  const filterRow = document.createElement("div");
  filterRow.className = "picker-row";

  const search = document.createElement("input");
  search.type = "search";
  search.className = "picker-search";
  search.placeholder = "Search Countries";
  search.setAttribute("aria-label", "Search Countries");
  search.addEventListener("input", () => {
    filters.search = search.value.trim().toLowerCase();
    renderList();
  });

  const makeSelect = (label, options, onchange) => {
    const wrap = document.createElement("label");
    wrap.className = "picker-field";
    const text = document.createElement("span");
    text.textContent = label;
    const select = document.createElement("select");
    for (const [i, option] of options.entries()) select.append(new Option(option, i));
    select.addEventListener("change", () => onchange(+select.value));
    wrap.append(text, select);
    return wrap;
  };

  const continentOptions = ["All Continents", ...continentNames];
  const continentSelect = makeSelect("Continent", continentOptions, (i) => {
    filters.continent = continentOptions[i];
    renderList();
  });
  const sortSelect = makeSelect("Sort By", allSorts.map((s) => s.label), (i) => {
    filters.sort = i;
    renderList();
  });

  const selectShown = makeButton("Select Shown", () => changeShown(true));
  const clearShown = makeButton("Deselect Shown", () => changeShown(false));

  filterRow.append(search, continentSelect, sortSelect, selectShown, clearShown);

  // Status Line and the List of Checkboxes
  const limitNote = document.createElement("div");
  limitNote.className = "picker-status picker-limit";
  limitNote.hidden = true;

  const status = document.createElement("div");
  status.className = "picker-status";
  status.setAttribute("role", "status");

  const list = document.createElement("div");
  list.className = "picker-list";
  list.setAttribute("role", "group");
  list.setAttribute("aria-label", "Countries");

  // Only the Picker's own "input" Event Announces a New Selection, not the Native Ones from the Controls Inside it
  for (const part of [presetRow, filterRow, list]) part.addEventListener("input", (event) => event.stopPropagation());

  root.append(presetRow, filterRow, limitNote, status, list);

  // The Countries that Pass the Search and Continent Filter, in the Chosen Order
  let shown = [];
  function visibleNames() {
    const {compare} = allSorts[filters.sort];
    return names
      .filter((n) => (filters.continent === "All Continents" || continents.get(n) === filters.continent) && n.toLowerCase().includes(filters.search))
      .sort((a, b) => compare(a, b) || d3.ascending(a, b));
  }

  // Draw the Checkbox List and the Status Line
  function renderList() {
    shown = visibleNames();
    d3.select(list)
      .selectAll("label")
      .data(shown, (d) => d)
      .join((enter) => {
        const label = enter.append("label").attr("class", "picker-item");
        label.append("input").attr("type", "checkbox").on("change", (event, d) => {
          presetIndex = null;
          const next = new Set(selected);
          if (event.target.checked) next.add(d);
          else next.delete(d);
          setSelection([...next]);
        });
        label.append("span").attr("class", "picker-name").text((d) => d);
        label.append("span").attr("class", "picker-detail").text((d) => detail(d));
        return label;
      })
      .order()
      .select("input")
      .property("checked", (d) => selected.has(d))
      .property("disabled", (d) => isFullScreen() && !selected.has(d) && selected.size >= fullScreenMax);

    if (shown.length === 0) {
      const empty = document.createElement("div");
      empty.className = "picker-empty";
      empty.textContent = "No Countries Match";
      list.replaceChildren(empty);
    } else list.querySelector(".picker-empty")?.remove();

    selectShown.disabled = clearShown.disabled = shown.length === 0;
    limitNote.hidden = !isFullScreen();
    limitNote.textContent = `Full Screen Shows Up to ${fullScreenMax} Countries`;
    status.textContent = `${selected.size} Selected · ${shown.length} of ${names.length} Shown · Your selection carries across Q2–Q4`;
    for (const [i, b] of presetButtons.entries()) {
      b.classList.toggle("is-active", i === presetIndex);
      b.setAttribute("aria-pressed", String(i === presetIndex));
    }
    countInput.hidden = presetIndex === null;
  }

  // Remember the Selection, Keeping Countries Chosen on Pages where they are not Available
  function save() {
    try {
      const kept = (readStored() ?? []).filter((n) => !nameSet.has(n));
      sessionStorage.setItem(STORAGE_KEY, JSON.stringify([...kept, ...selected]));
    } catch {}
  }

  function setSelection(picks) {
    selected.clear();
    for (const n of isFullScreen() ? picks.slice(0, fullScreenMax) : picks) selected.add(n);
    save();
    renderList();
    root.dispatchEvent(new Event("input", {bubbles: true}));
  }

  function applyPreset() {
    setSelection(presets[presetIndex].pick(+countInput.value));
  }

  function changeShown(on) {
    presetIndex = null;
    const next = new Set(selected);
    for (const n of shown) on ? next.add(n) : next.delete(n);
    setSelection([...next]);
  }

  // The Selected Names, Alphabetical, Read by Generators.input
  Object.defineProperty(root, "value", {get: () => names.filter((n) => selected.has(n))});

  // Entering Full Screen Trims the Selection to the Limit (Keeping the Full One); Leaving Restores it if Unchanged
  let stash = null;
  const onFullScreenChange = () => {
    if (!root.isConnected) return document.removeEventListener("fullscreenchange", onFullScreenChange);
    if (isFullScreen()) {
      stash = selected.size > fullScreenMax ? [...selected] : null;
      if (stash) setSelection(stash);
    } else if (stash) {
      const trimmed = stash.slice(0, fullScreenMax);
      if (selected.size === trimmed.length && trimmed.every((n) => selected.has(n))) setSelection(stash);
      stash = null;
    }
    renderList();
  };
  document.addEventListener("fullscreenchange", onFullScreenChange);

  renderList();
  return root;
}
