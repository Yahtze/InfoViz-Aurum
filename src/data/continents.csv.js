import {readFileSync} from "node:fs";

process.stdout.write(readFileSync("data/processed/continents.csv"));
