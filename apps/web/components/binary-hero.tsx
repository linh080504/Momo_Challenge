"use client";

import { useEffect, useRef } from "react";

const WORDS = ["DỪNG", "KIỂM"];
const FONT = '"Arial Black", system-ui, sans-serif';
const MONO = 'ui-monospace, "Cascadia Mono", Consolas, monospace';

type Cell = { x: number; y: number; digit: string; inWord: boolean; noise: number };

function noiseAt(column: number, row: number) {
  return ((Math.imul(column + 17, 73856093) ^ Math.imul(row + 9, 19349663)) >>> 0) % 997 / 997;
}

function makeCells(width: number, height: number, step: number): Cell[] {
  const mask = document.createElement("canvas");
  mask.width = width;
  mask.height = height;
  const ctx = mask.getContext("2d", { willReadFrequently: true });
  if (!ctx) return [];

  const mobile = width < 630;
  let fontSize = Math.round(height * (mobile ? .44 : .41));
  ctx.font = "950 " + fontSize + "px " + FONT;
  const widest = Math.max(...WORDS.map(word => ctx.measureText(word).width));
  fontSize = Math.min(fontSize, Math.floor(fontSize * width * (mobile ? .84 : .9) / widest));
  ctx.font = "950 " + fontSize + "px " + FONT;
  ctx.textAlign = "center";
  ctx.textBaseline = "alphabetic";
  for (const [index, word] of WORDS.entries()) {
    const metrics = ctx.measureText(word);
    const center = height * (index === 0 ? .235 : .735);
    const baseline = center + (metrics.actualBoundingBoxAscent - metrics.actualBoundingBoxDescent) / 2;
    ctx.fillText(word, width * (mobile ? .52 : .58), baseline);
  }
  const pixels = ctx.getImageData(0, 0, width, height).data;
  const cells: Cell[] = [];
  for (let row = 0, y = Math.floor(step / 2); y < height; y += step, row++) {
    for (let column = 0, x = Math.floor(step / 2); x < width; x += step, column++) {
      const noise = noiseAt(column, row);
      cells.push({
        x,
        y,
        digit: noise > .48 ? "1" : "0",
        inWord: pixels[(y * width + x) * 4 + 3] > 112,
        noise,
      });
    }
  }
  return cells;
}

export function BinaryHero() {
  const canvas = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    const surface = canvas.current;
    const area = surface?.closest("section");
    if (!surface || !area) return;
    const context = surface.getContext("2d");
    const base = document.createElement("canvas");
    const background = base.getContext("2d");
    if (!context || !background) return;

    const reducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)");
    let cells: Cell[] = [];
    let width = 0;
    let height = 0;
    let step = 14;
    let ratio = 1;
    let frame = 0;
    let pointer: { x: number; y: number } | null = null;

    function paint() {
      frame = 0;
      if (!context || !width || !height) return;
      context.clearRect(0, 0, width, height);
      context.drawImage(base, 0, 0, width, height);
      if (!pointer || reducedMotion.matches) return;

      const radius = width < 630 ? 83 : 142;
      for (const cell of cells) {
        const dx = cell.x - pointer.x;
        const dy = cell.y - pointer.y;
        if (Math.abs(dx) > radius || Math.abs(dy) > radius) continue;
        const strength = 1 - Math.hypot(dx, dy) / radius;
        if (strength <= 0) continue;
        context.fillStyle = "rgba(145, 6, 74, " + (strength * .76) + ")";
        const pull = strength * (cell.inWord ? .035 : .14);
        context.fillText(cell.digit, cell.x - dx * pull, cell.y - dy * pull);
      }
    }

    function schedule() {
      if (!frame) frame = window.requestAnimationFrame(paint);
    }

    const resize = () => {
      if (!surface || !context || !background) return;
      width = Math.floor(surface.clientWidth);
      height = Math.floor(surface.clientHeight);
      if (width < 1 || height < 1) return;
      step = width < 630 ? 9 : 13;
      ratio = Math.min(2, window.devicePixelRatio || 1);
      surface.width = base.width = Math.round(width * ratio);
      surface.height = base.height = Math.round(height * ratio);
      cells = makeCells(width, height, step);
      for (const layer of [context, background]) {
        layer.setTransform(ratio, 0, 0, ratio, 0, 0);
        layer.font = "750 " + Math.round(step * .83) + "px " + MONO;
        layer.textAlign = "center";
        layer.textBaseline = "middle";
      }
      for (const cell of cells) {
        const opacity = cell.inWord ? .63 + cell.noise * .29 : .065 + cell.noise * .12;
        background.fillStyle = "rgba(164, 16, 90, " + opacity + ")";
        background.fillText(cell.digit, cell.x, cell.y);
      }
      schedule();
    };

    const move = (event: PointerEvent) => {
      if (event.pointerType === "touch" || reducedMotion.matches) return;
      const bounds = surface.getBoundingClientRect();
      pointer = { x: event.clientX - bounds.left, y: event.clientY - bounds.top };
      schedule();
    };
    const leave = () => {
      pointer = null;
      schedule();
    };

    const observer = new ResizeObserver(resize);
    observer.observe(surface);
    area.addEventListener("pointermove", move);
    area.addEventListener("pointerleave", leave);
    reducedMotion.addEventListener("change", leave);
    return () => {
      observer.disconnect();
      area.removeEventListener("pointermove", move);
      area.removeEventListener("pointerleave", leave);
      reducedMotion.removeEventListener("change", leave);
      window.cancelAnimationFrame(frame);
    };
  }, []);

  return <canvas className="landing-binary" ref={canvas} aria-hidden="true" />;
}
