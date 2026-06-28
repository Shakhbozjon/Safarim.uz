/** @type {import('next').NextConfig} */
const nextConfig = {
  // Docker uchun minimal mustaqil (standalone) build → .next/standalone/server.js
  output: "standalone",
  images: {
    remotePatterns: [
      { protocol: "http", hostname: "localhost", port: "9000" },
      // Prod MinIO/CDN domeni (deploy paytida o'zgartiring):
      // { protocol: "https", hostname: "cdn.safarim.uz" },
    ],
  },
};

export default nextConfig;
