/** @type {import('next').NextConfig} */
const nextConfig = {
  // Docker uchun minimal mustaqil (standalone) build → .next/standalone/server.js
  output: "standalone",
  images: {
    remotePatterns: [
      { protocol: "http", hostname: "localhost", port: "9000" },
      // Prod MinIO media — cdn subdomen (nginx TLS proxy → minio:9000)
      { protocol: "https", hostname: "cdn.uzsafar.uz" },
    ],
  },
};

export default nextConfig;
