---
title: AI Disclosure
---

# AI Disclosure

We used AI tools to build this project. This page describes what they did and what we did ourselves.
The questions, the design choices, and the review of every result were ours.
AI worked as a tool for writing code and text, and we checked what it produced.

## Where AI Was Used

- **Data Processing.** The code that builds the data tables from the OWID dataset was written with AI, working from the questions we agreed on in Milestone 1.
- **Sketches.** The Matplotlib sketches were generated with AI from our written design choices.
- **This Site.** The Observable Framework app, its d3.js charts, its styling, and its page text were written with AI.
- **Project Writing.** AI helped draft the proposal and report text, which we then reviewed and edited.

## Who Did What

### Yathin Reddy Duvuru

**Tools:** Codex GPT 6-Sol (OpenAI) for the sketches and data code, and Claude Code with Sonnet 5.5 (Anthropic) for this site.

- AI wrote the code that builds the data tables from the full OWID dataset, given the Milestone 1 questions.
- I chose the plot types, color scales, color schemes, legends, and axis scales for the Q2–Q4 sketches. AI wrote and refined the Matplotlib code.
- For this site, I supplied a notebook from an earlier course assignment as a reference for the low-level d3.js style I wanted, and AI recreated the sketches in d3.js from it.
- AI also wrote the CSS for the interactive elements, including full screen, and the extra interactivity we added in response to feedback.
- I reviewed the generated code to confirm it uses the data tables correctly and implements the designs. Automated tests check data selection, source totals, and plot structure.

### Yusuke Katsuki

**Tools:** Claude Code (Anthropic) throughout, and Codex (OpenAI) for parts of the Milestone 2 report.

- Milestone 1: AI helped brainstorm the problem statement, dataset, and six questions, and draft the proposal text. I reviewed each section.
- Milestone 2: AI set up the repository and wrote the data build script, its checks, and the sensitivity table. I chose the minimal setup with two shared tables. I drafted the Q1, Q5, and Q6 chart forms, and AI refined them and wrote the plotting code. I reviewed the figures and requested changes.
- Milestone 3: AI wrote the d3.js code and page text for Q1, Q5, and Q6, including the changes made after Milestone 2 feedback and the matched-pair chart. I checked every page and opened the pull request.
- AI drafted my sections of the report from the page text and captured the chart images. I reviewed and edited them.
