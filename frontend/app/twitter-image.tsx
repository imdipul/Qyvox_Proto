import { createSocialImage, socialImageSize } from "@/lib/socialImage";

export const alt = "Qyvox — Prove the fact. Keep the data.";
export const size = socialImageSize;
export const contentType = "image/png";

export default function TwitterImage() {
  return createSocialImage();
}
