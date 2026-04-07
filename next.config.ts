import type { NextConfig } from 'next'

const nextConfig: NextConfig = {
  reactCompiler: true,
  async rewrites() {
    return [
      // Proxy API requests to FastAPI backend
      {
        source: '/api/backend/:path*',
        destination: '/backend/:path*',
      },
    ]
  },
}

export default nextConfig
