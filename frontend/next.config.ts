import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  async rewrites() {
    return [
      {
        source: "/api_backend/:path*",
        destination: "http://13.53.126.59:8000/:path*",
      },
    ];
  },
};

export default nextConfig;
