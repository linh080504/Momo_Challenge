// Nén ảnh ở trình duyệt TRƯỚC khi gửi (DECISIONS 2026-11-24): cạnh dài ≤ 1600px, JPEG, rồi base64.
// Ảnh điện thoại 4–12 MB sẽ đụng trần 5 MB của API và làm chậm p95, nên nén ở client.

export const MAX_EDGE_PX = 1600;
/** Trần của API (byte gốc, trước khi base64). */
export const MAX_IMAGE_BYTES = 5 * 1024 * 1024;
const QUALITY_STEPS = [0.85, 0.7, 0.55];

export interface PreparedImage {
  /** base64 thuần, KHÔNG có tiền tố "data:...". Khớp hợp đồng POST /v1/analyze. */
  base64: string;
  mime: "image/jpeg";
  /** URL tạm để xem trước. Phải gọi URL.revokeObjectURL khi bỏ ảnh. */
  previewUrl: string;
  name: string;
  bytesBefore: number;
  bytesAfter: number;
  width: number;
  height: number;
}

/** Lỗi có thông điệp tiếng Việt, đưa thẳng cho người dùng đọc. */
export class ImageError extends Error {}

function canvasToBlob(canvas: HTMLCanvasElement, quality: number): Promise<Blob | null> {
  return new Promise((resolve) => canvas.toBlob(resolve, "image/jpeg", quality));
}

function blobToBase64(blob: Blob): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onerror = () => reject(reader.error);
    reader.onload = () => {
      const result = String(reader.result);
      resolve(result.slice(result.indexOf(",") + 1));
    };
    reader.readAsDataURL(blob);
  });
}

export async function prepareImage(file: File): Promise<PreparedImage> {
  if (!file.type.startsWith("image/")) {
    throw new ImageError("Tệp này không phải ảnh. Hãy chọn ảnh chụp màn hình tin nhắn (PNG hoặc JPEG).");
  }

  let bitmap: ImageBitmap;
  try {
    bitmap = await createImageBitmap(file);
  } catch {
    throw new ImageError("Không đọc được ảnh này. Hãy chọn một ảnh PNG hoặc JPEG khác.");
  }

  // Lưu kích thước gốc ngay: sau bitmap.close() width/height về 0.
  const srcWidth = bitmap.width;
  const srcHeight = bitmap.height;
  const scale = Math.min(1, MAX_EDGE_PX / Math.max(srcWidth, srcHeight));
  const width = Math.max(1, Math.round(srcWidth * scale));
  const height = Math.max(1, Math.round(srcHeight * scale));

  const canvas = document.createElement("canvas");
  canvas.width = width;
  canvas.height = height;
  const ctx = canvas.getContext("2d");
  if (!ctx) {
    bitmap.close();
    throw new ImageError("Trình duyệt này không xử lý được ảnh. Hãy thử trình duyệt khác.");
  }
  // JPEG không có nền trong suốt; PNG có nền trong suốt sẽ thành đen nếu không tô trắng trước.
  ctx.fillStyle = "#ffffff";
  ctx.fillRect(0, 0, width, height);
  ctx.drawImage(bitmap, 0, 0, width, height);
  bitmap.close();

  let blob: Blob | null = null;
  for (const quality of QUALITY_STEPS) {
    blob = await canvasToBlob(canvas, quality);
    if (blob && blob.size <= MAX_IMAGE_BYTES) break;
  }
  if (!blob || blob.size > MAX_IMAGE_BYTES) {
    throw new ImageError("Ảnh này quá lớn. Hãy cắt bớt phần thừa hoặc chọn ảnh khác.");
  }

  const base64 = await blobToBase64(blob);
  console.info(
    `[nén ảnh] ${file.name || "ảnh dán"}: ${(file.size / 1024).toFixed(0)} KB → ${(blob.size / 1024).toFixed(0)} KB, ${srcWidth}×${srcHeight} → ${width}×${height}`,
  );

  return {
    base64,
    mime: "image/jpeg",
    previewUrl: URL.createObjectURL(blob),
    name: file.name || "Ảnh đã dán",
    bytesBefore: file.size,
    bytesAfter: blob.size,
    width,
    height,
  };
}
