"use client";

import { useEffect, useId, useState } from "react";
import { FileImage, ImageUp, X } from "lucide-react";

export function Upload({ file, onChange, disabled = false }: {
  file: File | null;
  onChange: (file: File | null) => void;
  disabled?: boolean;
}) {
  const id = useId();
  const [dragging, setDragging] = useState(false);
  const [preview, setPreview] = useState<string | null>(null);

  useEffect(() => {
    if (!file || !["image/png", "image/jpeg"].includes(file.type)) {
      setPreview(null);
      return;
    }
    const url = URL.createObjectURL(file);
    setPreview(url);
    return () => URL.revokeObjectURL(url);
  }, [file]);

  return (
    <div className={"upload" + (dragging ? " dragging" : "")}
      onDragOver={event => { event.preventDefault(); if (!disabled) setDragging(true); }}
      onDragLeave={() => setDragging(false)}
      onDrop={event => {
        event.preventDefault();
        setDragging(false);
        if (!disabled && event.dataTransfer.files[0]) onChange(event.dataTransfer.files[0]);
      }}>
      <input id={id} className="visually-hidden" type="file" accept="image/png,image/jpeg" disabled={disabled}
        aria-label="Chọn ảnh PNG hoặc JPEG"
        onChange={event => {
          if (event.target.files?.[0]) onChange(event.target.files[0]);
          event.target.value = "";
        }} />
      <label className="upload-target" htmlFor={id}>
        <span className="upload-icon" aria-hidden="true">
          {file && preview ? <img className="upload-preview" src={preview} alt="" width={42} height={42} /> :
            file ? <FileImage size={22} /> : <ImageUp size={22} />}
        </span>
        <span><strong>{file ? file.name : "Tải ảnh chụp"}</strong><small>{file ? "Bấm để đổi ảnh" : "PNG hoặc JPEG · Kéo thả hoặc chọn ảnh"}</small></span>
      </label>
      {file && <button type="button" className="icon-button" disabled={disabled} aria-label="Gỡ ảnh" onClick={() => onChange(null)}><X size={19} /></button>}
    </div>
  );
}
