/** @type {import('next').NextConfig} */
const nextConfig = {
  async rewrites() {
    const backend = process.env.NEXT_PUBLIC_ARIA_API_URL || "http://127.0.0.1:8000";
    const voice = process.env.NEXT_PUBLIC_ARIA_VOICE_URL || "http://127.0.0.1:8001";
    return [
      { source: "/role3/:path*", destination: `${backend}/:path*` },
      { source: "/role1/:path*", destination: `${voice}/:path*` },
    ];
  },
};

export default nextConfig;
