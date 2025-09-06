/** @type {import('next').NextConfig} */
const nextConfig = {
  // API proxy to backend during development
  async rewrites() {
    return process.env.NODE_ENV === 'development' ? [
      {
        source: '/api/:path*',
        destination: 'http://localhost:8000/:path*', // FastAPI backend
      },
    ] : [];
  },
  
  // Security headers
  async headers() {
    return [
      {
        source: '/(.*)',
        headers: [
          {
            key: 'X-Frame-Options',
            value: 'DENY',
          },
          {
            key: 'X-Content-Type-Options',
            value: 'nosniff',
          },
          {
            key: 'Referrer-Policy',
            value: 'origin-when-cross-origin',
          },
        ],
      },
    ];
  },
  
  // Enable experimental features
  experimental: {
    // Enable if needed for performance
  },
  
  // Image optimization
  images: {
    remotePatterns: [
      // Add patterns for external images if needed
    ],
  },
};

module.exports = nextConfig;