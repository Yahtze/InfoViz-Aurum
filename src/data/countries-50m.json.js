import {readFileSync} from "node:fs";

process.stdout.write(readFileSync("data/raw/world-atlas-2.0.2-countries-50m.json"));
