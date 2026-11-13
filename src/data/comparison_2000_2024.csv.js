import {readFileSync} from "node:fs";

process.stdout.write(readFileSync("data/processed/comparison_2000_2024.csv"));
