/** @type {import('next').NextConfig} */
const nextConfig = {
  // Docker uchun minimal mustaqil (standalone) build → .next/standalone/server.js
  output: "standalone",
  images: {
    // Optimizator kesh yozuvini HAR BIR (kenglik × format) uchun alohida
    // saqlaydi — ro'yxat uzun bo'lsa, tashqaridan har xil `w` qiymatlari
    // bilan so'rov yuborib diskni shishirish mumkin (bu Next 14 dagi ochiq
    // ogohlantirishlardan biri). Bizda `next/image` faqat avatarda va
    // `sizes="80px"` bilan ishlatiladi, shuning uchun ro'yxatni qisqartiramiz:
    // 8+8 = 16 ta variant o'rniga 5 ta qoladi.
    imageSizes: [64, 128, 256],
    deviceSizes: [640, 1080],
    remotePatterns: [
      { protocol: "http", hostname: "localhost", port: "9000" },
      // Prod MinIO media — cdn subdomen (nginx TLS proxy → minio:9000)
      { protocol: "https", hostname: "cdn.uzsafar.uz" },
    ],
  },
};

export default nextConfig;
