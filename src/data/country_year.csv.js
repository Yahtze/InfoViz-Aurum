import {readFileSync} from "node:fs";

process.stdout.write(readFileSync("data/processed/country_year.csv"));
