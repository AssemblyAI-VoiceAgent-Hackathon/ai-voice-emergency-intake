/** @type {import('next').NextConfig} */
const nextConfig = {
  async rewrites() {
    const backend = process.env.NEXT_PUBLIC_ARIA_API_URL || "http://127.0.0.1:8000";
    return [{ source: "/role3/:path*", destination: `${backend}/:path*` }];
  },
};

export default nextConfig;
