const fs = require("node:fs");
const path = require("node:path");

async function main() {
  const [mode, width, height] = process.argv.slice(2);
  const image = fs.readFileSync(0);
  if (mode === "qr") {
    const jsQR = require("jsqr");
    const pixels = new Uint8ClampedArray(image.buffer, image.byteOffset, image.byteLength);
    const qr = jsQR(pixels, Number(width), Number(height));
    process.stdout.write(qr?.data || "");
    return;
  }
  if (mode !== "ocr") throw new Error("Unknown media operation");
  const { createWorker, PSM } = require("tesseract.js");
  const langPath = path.join(__dirname, "node_modules", ".tkc-tessdata");
  const worker = await createWorker("vie+eng", 1, { langPath, cacheMethod: "none", gzip: true });
  try {
    await worker.setParameters({ tessedit_pageseg_mode: PSM.SPARSE_TEXT });
    const { data } = await worker.recognize(image);
    process.stdout.write(data.text);
  } finally {
    await worker.terminate();
  }
}

main().catch(() => {
  process.exitCode = 1;
});
