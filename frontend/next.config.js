// 显示环境变量信息
console.log('🌍 Frontend Environment Configuration:');
console.log('=====================================');

// 检查不同的环境文件
const fs = require('fs');
const path = require('path');

const envFiles = [
  '.env.local',
  '.env.development',
  '.env',
  'environment.local',
  'environment.example'
];

let envPath = null;
let envFile = null;

for (const file of envFiles) {
  const fullPath = path.resolve(process.cwd(), file);
  if (fs.existsSync(fullPath)) {
    envPath = fullPath;
    envFile = file;
    break;
  }
}

if (envPath) {
  console.log(`📁 Environment file: ${envPath}`);
  
  const envContent = fs.readFileSync(envPath, 'utf8');
  const envVars = {};
  
  envContent.split('\n').forEach(line => {
    const trimmed = line.trim();
    if (trimmed && !trimmed.startsWith('#')) {
      const [key, ...valueParts] = trimmed.split('=');
      if (key && valueParts.length > 0) {
        const value = valueParts.join('=');
        envVars[key] = value;
      }
    }
  });
  
  console.log('🔧 Environment variables:');
  Object.entries(envVars).forEach(([key, value]) => {
    // 隐藏敏感信息
    if (key.toLowerCase().includes('key') || key.toLowerCase().includes('secret') || key.toLowerCase().includes('password')) {
      console.log(`   ${key}: ${'*'.repeat(Math.min(value.length, 8))}`);
    } else {
      console.log(`   ${key}: ${value}`);
    }
  });
} else {
  console.log('⚠️  No environment file found');
}

// 显示当前环境信息
console.log('🌐 Current environment:');
console.log(`   NODE_ENV: ${process.env.NODE_ENV || 'development'}`);
console.log(`   NEXT_PUBLIC_ENVIRONMENT: ${process.env.NEXT_PUBLIC_ENVIRONMENT || 'local'}`);

// 显示 keys 目录信息
console.log('🔑 Keys directory information:');
const keysDirFromEnv = process.env.FRONTEND_KEYS_DIRECTORY;
const keysDir = keysDirFromEnv 
  ? (path.isAbsolute(keysDirFromEnv) ? keysDirFromEnv : path.resolve(process.cwd(), keysDirFromEnv))
  : path.resolve(process.cwd(), 'keys');

console.log(`   FRONTEND_KEYS_DIRECTORY: ${keysDirFromEnv || '(not set, using default)'}`);
console.log(`   Resolved keys directory: ${keysDir}`);

if (fs.existsSync(keysDir)) {
  const keyFiles = fs.readdirSync(keysDir).filter(file => file.endsWith('.pem'));
  if (keyFiles.length > 0) {
    console.log('   Available key files:');
    keyFiles.forEach(file => {
      console.log(`     - ${file}`);
    });
  } else {
    console.log('   ⚠️  No .pem key files found');
  }
} else {
  console.log('   ❌ Keys directory not found');
}

// 显示 JWT key 路径
console.log('🔐 JWT key paths:');
const jwtPrivatePath = process.env.FRONTEND_JWT_PRIVATE_KEY_PATH || './keys/frontend_jwt_private_key.pem';
const jwtPublicPath = process.env.FRONTEND_JWT_PUBLIC_KEY_PATH || './keys/frontend_jwt_public_key.pem';
console.log(`   JWT Private Key: ${path.resolve(process.cwd(), jwtPrivatePath)}`);
console.log(`   JWT Public Key: ${path.resolve(process.cwd(), jwtPublicPath)}`);

console.log('=====================================');

/** @type {import('next').NextConfig} */
const nextConfig = {
  env: {
    NEXT_PUBLIC_API_URL: process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000',
    NEXT_PUBLIC_APP_NAME: process.env.NEXT_PUBLIC_APP_NAME || 'SupplyNexus Fulfillment Service',
  },
  // Removed incorrect API mapping - Next.js should have its own API routes
  // async rewrites() {
  //   return [
  //     {
  //       source: '/api/:path*',
  //       destination: `${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'}/api/:path*`,
  //     },
  //   ];
  // },
  images: {
    domains: [
      'localhost',
      'admin.supplynexus.store',
      'supplynexus.store',
      'api.supplynexus.store',
      'images.printify.com',
    ],
  },
  // Enable strict mode for better dev experience
  reactStrictMode: true,
  
  // Temporarily disable ESLint and TypeScript during build
  eslint: {
    ignoreDuringBuilds: true,
  },
  typescript: {
    ignoreBuildErrors: true,
  },
  
  // Webpack configuration for path aliases
  webpack: (config, { buildId, dev, isServer, defaultLoaders, webpack }) => {
    config.resolve.alias = {
      ...config.resolve.alias,
      '@': require('path').resolve(__dirname, 'src'),
    };
    return config;
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
          {
            key: 'X-XSS-Protection',
            value: '1; mode=block',
          },
        ],
      },
    ];
  },
  
  // Output configuration for Docker
  output: 'standalone',
  
  // Experimental features
  experimental: {
    // Removed outputFileTracingRoot as it's no longer needed in Next.js 15
  },
};

module.exports = nextConfig;
