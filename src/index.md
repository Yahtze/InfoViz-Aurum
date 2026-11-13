---
title: Overview
---

# Aurum: Cleaner Share, More Fossil Power?

**Team Aurum** · Yathin Reddy Duvuru, Yusuke Katsuki · CS-GY 6313 Information Visualization, NYU, Fall 2026

## Abstract

Many countries have raised the share of their electricity that comes from clean sources.
A rising share is often read as progress away from fossil fuels, but a share is a ratio: it can climb while fossil generation stays flat, or even grows, if total demand grows faster.
We ask whether countries that raised their clean share between 2000 and 2024 also generated less electricity from fossil fuels, and what separates the countries that did from those that did not.
This site presents our answers as a set of interactive visualizations, one for each of six guiding questions.

## 1. Introduction

Decarbonizing electricity is central to most national climate strategies, and progress is usually reported as the clean share of generation: the fraction supplied by renewables and nuclear power.
The measure is easy to compare across countries and years, which makes it a natural headline number.
It is also easy to over-read.
Because it is a proportion, it says nothing on its own about how much fossil-fuel electricity a country still burns.
A country that doubles its clean generation while its demand triples has a falling share of fossil power and a rising amount of it.

We examine this gap using country-level electricity data from Our World in Data (OWID) for 2000–2024.
We compare the 108 countries with data at both endpoints and at least 10 TWh of generation in 2024, so that very small systems do not dominate the extremes.
Clean electricity here means renewables plus nuclear.
Of the 79 countries in this set that raised their clean share, 44 still generated more fossil-fuel electricity in 2024 than in 2000.
That split motivates the rest of the project: a higher clean share and lower fossil generation are related, but they are not the same outcome.

Our visualizations are built to let a reader move between the two views, share and absolute generation, and to see which countries, sources, and starting conditions account for the difference.

## 2. Research Questions and Visualizations

Each question has its own interactive page.

<ol>
  <li>
    <strong>Global Mix.</strong>
    How has the global electricity mix changed from 2000 to 2024, in both percentage shares and absolute generation (TWh)?
    <em>In progress.</em>
  </li>
  <li>
    <strong><a href="./q2">Clean Share by Country.</a></strong>
    How do countries compare in their clean electricity shares in 2024, and which have the highest and lowest shares?
  </li>
  <li>
    <strong><a href="./q3">Largest Changes in Clean Share.</a></strong>
    Which countries experienced the largest increases or decreases in clean share between 2000 and 2024?
  </li>
  <li>
    <strong><a href="./q4">Clean Source Contributions.</a></strong>
    In the countries with the largest increases in clean share, how much did wind, solar, hydro, nuclear, and other clean sources each contribute?
  </li>
  <li>
    <strong>Clean Share Versus Fossil Generation.</strong>
    Which countries increased their clean share while also reducing fossil-fuel generation, and which increased their clean share but still generated more?
    <em>In progress.</em>
  </li>
  <li>
    <strong>Demand Growth and Starting Mix.</strong>
    How do electricity demand growth and the initial mix in 2000 differ between countries that reduced fossil-fuel generation and those that did not?
    <em>In progress.</em>
  </li>
</ol>

## 3. Data and Approach

All figures are drawn from a pinned copy of the OWID energy dataset, processed into two tables: a country-by-year table for 2000–2024 and a per-country comparison of the 2000 and 2024 endpoints.
Countries with an unknown clean share are excluded from rankings rather than treated as zero, and ties in rankings are broken by country name.
Changes in share are reported in percentage points, and changes in output in terawatt-hours.
Source-level breakdowns are an accounting decomposition of the change, not evidence of cause.
