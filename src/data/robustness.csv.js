import {readFileSync} from "node:fs";

process.stdout.write(readFileSync("data/processed/robustness.csv"));
