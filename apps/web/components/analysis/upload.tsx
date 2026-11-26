"use client";

import { useEffect, useId, useState } from "react";
import { FileImage, ImageUp, Mic, X } from "lucide-react";

export function Upload({ file, onChange, disabled = false, mode = "image" }: {
  file: File | null;
  onChange: (file: File | null) => void;
  disabled?: boolean;
  mode?: "image" | "receipt" | "audio";
}) {
  const id = useId();
  const [dragging, setDragging] = useState(false);
  const [preview, setPreview] = useState<string | null>(null);

  useEffect(() => {
    if (!file || !["image/png", "image/jpeg"].includes(file.type)) {
      // An invalid or cleared file drops the existing blob preview.
      // eslint-disable-next-line react-hooks/set-state-in-effect
      setPreview(null);
      return;
    }
    const url = URL.createObjectURL(file);
    setPreview(url);
    return () => URL.revokeObjectURL(url);
  }, [file]);

  const audio = mode === "audio";
  const label = audio ? "Tải bản ghi âm" : mode === "receipt" ? "Tải ảnh biên lai gốc" : "Tải ảnh chụp";
  return (
    <div className={"upload" + (dragging ? " dragging" : "")}
      onDragOver={event => { event.preventDefault(); if (!disabled) setDragging(true); }}
      onDragLeave={() => setDragging(false)}
      onDrop={event => {
        event.preventDefault();
        setDragging(false);
        if (!disabled && event.dataTransfer.files[0]) onChange(event.dataTransfer.files[0]);
      }}>
      <input id={id} className="visually-hidden" type="file" accept={audio ? "audio/*,.wav,.mp3,.m4a" : "image/png,image/jpeg"} disabled={disabled}
        aria-label={audio ? "Chọn tệp ghi âm" : "Chọn ảnh PNG hoặc JPEG"}
        onChange={event => {
          if (event.target.files?.[0]) onChange(event.target.files[0]);
          event.target.value = "";
        }} />
      <label className="upload-target" htmlFor={id}>
        <span className="upload-icon" aria-hidden="true">
          {audio ? <Mic size={22} /> : file && preview ? <img className="upload-preview" src={preview} alt="" width={42} height={42} /> :
            file ? <FileImage size={22} /> : <ImageUp size={22} />}
        </span>
        <span><strong>{file ? file.name : label}</strong><small>{file ? "Bấm để đổi tệp" : audio ? "WAV, MP3 hoặc M4A · Tối đa 45 giây" : "PNG hoặc JPEG · Kéo thả hoặc chọn ảnh"}</small></span>
      </label>
      {file && <button type="button" className="icon-button" disabled={disabled} aria-label={audio ? "Gỡ bản ghi" : "Gỡ ảnh"} onClick={() => onChange(null)}><X size={19} /></button>}
    </div>
  );
}
