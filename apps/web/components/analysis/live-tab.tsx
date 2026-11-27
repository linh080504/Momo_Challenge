"use client";

import { useEffect, useRef, useState } from "react";
import { Camera, Monitor, Square, Video } from "lucide-react";

type TabCaptureOptions = DisplayMediaStreamOptions & {
  selfBrowserSurface: "exclude";
  monitorTypeSurfaces: "exclude";
  surfaceSwitching: "exclude";
};

export function LiveTab({ disabled, onCapture }: { disabled: boolean; onCapture: (file: File) => void }) {
  const video = useRef<HTMLVideoElement>(null);
  const stream = useRef<MediaStream | null>(null);
  const mounted = useRef(false);
  const [sharing, setSharing] = useState(false);
  const [requesting, setRequesting] = useState(false);
  const [ready, setReady] = useState(false);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState("");

  useEffect(() => {
    mounted.current = true;
    return () => {
      mounted.current = false;
      stream.current?.getTracks().forEach(track => track.stop());
    };
  }, []);

  function stop() {
    const previous = stream.current;
    stream.current = null;
    previous?.getTracks().forEach(track => track.stop());
    if (video.current) video.current.srcObject = null;
    setSharing(false);
    setReady(false);
  }

  async function start() {
    if (!navigator.mediaDevices?.getDisplayMedia) {
      setMessage("Trình duyệt này chưa hỗ trợ chia sẻ tab. Bạn có thể tải ảnh chụp bên dưới.");
      return;
    }
    setRequesting(true);
    setMessage("");
    try {
      const options: TabCaptureOptions = {
        video: { displaySurface: "browser", frameRate: { ideal: 8 }, width: { ideal: 1600 } },
        audio: false, selfBrowserSurface: "exclude", monitorTypeSurfaces: "exclude", surfaceSwitching: "exclude",
      };
      const selected = await navigator.mediaDevices.getDisplayMedia(options);
      const track = selected.getVideoTracks()[0];
      if (!mounted.current || !video.current || !track || track.getSettings().displaySurface !== "browser") {
        selected.getTracks().forEach(item => item.stop());
        if (mounted.current) setMessage("Hãy chọn một tab trình duyệt. Bạn cũng có thể tải ảnh chụp bên dưới.");
        return;
      }
      stream.current = selected;
      track.addEventListener("ended", () => { if (stream.current === selected) stop(); }, { once: true });
      video.current.srcObject = selected;
      setSharing(true);
    } catch (failure) {
      if (mounted.current) setMessage(failure instanceof DOMException && failure.name === "NotAllowedError" ?
        "Bạn chưa cấp quyền chia sẻ tab." : "Chưa kết nối được với tab. Hãy thử lại hoặc tải ảnh chụp.");
    } finally {
      if (mounted.current) setRequesting(false);
    }
  }

  function capture() {
    const source = video.current;
    if (!source?.videoWidth || !source.videoHeight || !stream.current) return;
    const canvas = document.createElement("canvas");
    const scale = Math.min(1, 1600 / Math.max(source.videoWidth, source.videoHeight));
    canvas.width = Math.max(1, Math.round(source.videoWidth * scale));
    canvas.height = Math.max(1, Math.round(source.videoHeight * scale));
    const context = canvas.getContext("2d");
    if (!context) return;
    context.drawImage(source, 0, 0, canvas.width, canvas.height);
    setSaving(true);
    canvas.toBlob(blob => {
      if (!mounted.current) return;
      setSaving(false);
      if (!blob) {
        setMessage("Chưa lưu được khung hình. Hãy thử chụp lại.");
        return;
      }
      onCapture(new File([blob], "khung-hinh-website.jpg", { type: "image/jpeg" }));
      setMessage("Đã chọn khung hình. Bấm Phân tích website để gửi ảnh cùng URL.");
    }, "image/jpeg", .88);
  }

  return <section className="live-tab" aria-label="Xem tab trực tiếp">
    <h3><Video size={19} aria-hidden="true" /> Xem tab trực tiếp</h3>
    <div className="live-tab-screen" data-sharing={sharing}>
      <video ref={video} aria-label="Hình ảnh tab đang chia sẻ" data-active={sharing} autoPlay muted playsInline
        onLoadedData={() => setReady(Boolean(stream.current))} />
      {!sharing && <p><Monitor size={26} aria-hidden="true" /> Chọn một tab đang hiển thị để xem và chụp khung hình.</p>}
    </div>
    <div className="actions">
      {sharing ? <>
        <button type="button" className="button secondary" onClick={stop}><Square size={17} /> Dừng chia sẻ</button>
        <button type="button" className="button secondary" disabled={disabled || !ready || saving} onClick={capture}>
          <Camera size={18} /> Chụp khung hình
        </button>
      </> : <button type="button" className="button secondary" disabled={disabled || requesting} onClick={start}>
        <Monitor size={18} /> {requesting ? "Đang chờ chọn tab…" : "Chia sẻ tab"}
      </button>}
    </div>
    <p className="micro muted">Hình trực tiếp hiển thị trên máy bạn. Chỉ khung hình đã chọn được gửi khi bấm phân tích. Hãy chọn đúng tab của URL đã nhập.</p>
    {message && <p role="status" className="muted">{message}</p>}
  </section>;
}
