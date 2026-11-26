import type { Input } from "./api";

export function readBase64(file: Blob): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve((reader.result as string).split(",", 2)[1]);
    reader.onerror = () => reject(new Error("Không đọc được tệp."));
    reader.readAsDataURL(file);
  });
}

export async function receiptInput(file: File): Promise<Input["image_base64"]> {
  if (!["image/png", "image/jpeg"].includes(file.type)) throw new Error("Hãy chọn ảnh biên lai PNG hoặc JPEG.");
  if (file.size > 5 * 1024 * 1024) throw new Error("Ảnh biên lai gốc phải nhỏ hơn 5 MB.");
  return readBase64(file);
}

export async function imageInput(file: File): Promise<Pick<Input, "image_base64" | "image_mime">> {
  if (!["image/png", "image/jpeg"].includes(file.type)) {
    throw new Error("Hãy chọn ảnh PNG hoặc JPEG.");
  }
  if (file.size > 30 * 1024 * 1024) throw new Error("Ảnh quá lớn. Hãy chọn ảnh nhỏ hơn 30 MB để nén.");
  const bitmap = await createImageBitmap(file).catch(() => {
    throw new Error("Ảnh hỏng hoặc không đọc được.");
  });
  try {
    const scale = Math.min(1, 1600 / Math.max(bitmap.width, bitmap.height));
    const canvas = document.createElement("canvas");
    canvas.width = Math.max(1, Math.round(bitmap.width * scale));
    canvas.height = Math.max(1, Math.round(bitmap.height * scale));
    const context = canvas.getContext("2d");
    if (!context) throw new Error("Trình duyệt không hỗ trợ xử lý ảnh.");
    context.fillStyle = "#fff";
    context.fillRect(0, 0, canvas.width, canvas.height);
    context.drawImage(bitmap, 0, 0, canvas.width, canvas.height);
    const encoded = canvas.toDataURL("image/jpeg", 0.86).split(",", 2)[1];
    if (!encoded || encoded.length > 4 * Math.ceil(5 * 1024 * 1024 / 3)) {
      throw new Error("Ảnh sau khi nén vẫn vượt quá 5 MB.");
    }
    return { image_base64: encoded, image_mime: "image/jpeg" };
  } finally {
    bitmap.close();
  }
}
