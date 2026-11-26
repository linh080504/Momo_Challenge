import Image from "next/image";

export const projectName = "PayPause AI";

export function BrandMascot({ size }: { size: number }) {
  return <Image src="/tro-ly-tho-hong.webp" width={size} height={size} alt="" loading="eager" unoptimized />;
}
