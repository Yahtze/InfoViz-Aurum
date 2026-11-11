---
title: Overview
---

# Aurum: Cleaner Share, More Fossil Power?

Many countries raised the share of clean electricity between 2000 and 2024.
Did they also generate less electricity from fossil fuels?

```js
const countryYear = await FileAttachment("data/country_year.csv").csv({typed: true});
const world = countryYear.filter((d) => d.country === "World");
```

```js
Plot.plot({
  title: "World Clean Electricity Share, 2000–2024",
  y: {label: "Clean Share (%)", grid: true},
  x: {label: "Year", tickFormat: "d"},
  marks: [Plot.lineY(world, {x: "year", y: "clean_share_pct"})]
})
```

This placeholder confirms the data loaders work. Replace it with the D3 views for Q1–Q6.
