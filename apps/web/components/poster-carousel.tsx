"use client";

import Image from "next/image";
import { useEffect, useState } from "react";
import { Pause, Play } from "lucide-react";

const posters = [
  {
    src: "/black-friday-canh-bao.webp",
    title: "Black Friday",
    alt: "Black Friday — Thủ đoạn lừa đảo bằng AI. Dừng lại, kiểm tra, xác minh.",
  },
  {
    src: "/shop-gia-canh-bao.webp",
    title: "Shop giả",
    alt: "Shop giả — Kiểm tra trước khi đặt cọc.",
  },
  {
    src: "/giong-noi-gia-canh-bao.webp",
    title: "Giọng nói giả",
    alt: "Giọng nói giả — Gọi lại số đã lưu.",
  },
] as const;

const interval = 6500;
const sizes = "(max-width: 380px) 225px, (max-width: 750px) 275px, (max-width: 960px) 320px, 450px";

export function PosterCarousel() {
  const [active, setActive] = useState(0);
  const [playing, setPlaying] = useState(false);
  const [reading, setReading] = useState(false);

  useEffect(() => {
    const motion = window.matchMedia("(prefers-reduced-motion: reduce)");
    const sync = () => setPlaying(!motion.matches);
    sync();
    motion.addEventListener("change", sync);
    return () => motion.removeEventListener("change", sync);
  }, []);

  useEffect(() => {
    if (!playing || reading) return;
    const timer = window.setTimeout(() => setActive(index => (index + 1) % posters.length), interval);
    return () => window.clearTimeout(timer);
  }, [active, playing, reading]);

  function step(direction: number) {
    setActive(index => (index + direction + posters.length) % posters.length);
  }

  return (
    <div className="landing-poster-carousel" role="region" aria-roledescription="băng chuyền"
      aria-label="Poster cảnh báo lừa đảo">
      <div className="landing-poster" aria-live={playing ? "off" : "polite"}
        onPointerEnter={event => { if (event.pointerType === "mouse") setReading(true); }}
        onPointerLeave={() => setReading(false)}>
        <div className="poster-track" style={{ transform: "translateX(-" + active * 100 + "%)" }}>
          {posters.map(({ src, alt, title }, index) => (
            <figure key={src} className="poster-slide" aria-hidden={index !== active}
              aria-label={title + " · " + (index + 1) + " / " + posters.length}>
              <Image src={src} alt={alt} width={960} height={1280} sizes={sizes}
                preload={index === 0} loading={index === 0 ? undefined : "eager"} />
            </figure>
          ))}
        </div>
      </div>
      <div className="poster-controls">
        <button type="button" className="poster-control" onClick={() => step(-1)} aria-label="Poster trước">Trước</button>
        <div className="poster-indicators" role="group" aria-label="Chọn poster">
          {posters.map(({ title }, index) => (
            <button type="button" key={title} onClick={() => setActive(index)}
              aria-label={"Xem poster " + title} aria-current={active === index ? true : undefined} />
          ))}
        </div>
        <button type="button" className="poster-control" onClick={() => step(1)} aria-label="Poster tiếp theo">Sau</button>
        <button type="button" className="poster-control poster-toggle" onClick={() => setPlaying(value => !value)}
          aria-label={playing ? "Tạm dừng tự chuyển poster" : "Bật tự chuyển poster"}
          title={playing ? "Tạm dừng tự chuyển" : "Bật tự chuyển"}>
          {playing ? <Pause size={16} aria-hidden="true" /> : <Play size={16} aria-hidden="true" />}
        </button>
      </div>
    </div>
  );
}
