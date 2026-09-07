import type { MetadataRoute } from "next";

/**
 * "Bosh ekranga qo'shish" uchun. Busiz telefonda saqlangan yorliq nomsiz va
 * ikonkasiz kvadrat bo'lib chiqardi.
 */
export default function manifest(): MetadataRoute.Manifest {
  return {
    name: "UzSafar — O'zbekiston bo'ylab arzon safar",
    short_name: "UzSafar",
    description:
      "Haydovchi va yo'lovchilarni bog'lovchi carpooling platformasi. Haydovchini o'zingiz tanlaysiz.",
    start_url: "/",
    display: "standalone",
    background_color: "#ffffff",
    theme_color: "#3b5bdb",
    lang: "uz",
    icons: [
      { src: "/icon.svg", sizes: "any", type: "image/svg+xml" },
    ],
  };
}
