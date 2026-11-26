const fs = require("node:fs");
const path = require("node:path");

const destination = path.join(__dirname, "node_modules", ".tkc-tessdata");
fs.mkdirSync(destination, { recursive: true });
for (const code of ["vie", "eng"]) {
  const source = path.dirname(require.resolve("@tesseract.js-data/" + code + "/package.json"));
  const file = code + ".traineddata.gz";
  fs.copyFileSync(path.join(source, "4.0.0_best_int", file), path.join(destination, file));
}
