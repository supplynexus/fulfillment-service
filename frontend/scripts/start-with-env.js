#!/usr/bin/env node

/**
 * Frontend 启动脚本 - 显示环境变量信息
 */

const fs = require('fs');
const path = require('path');
const { spawn } = require('child_process');

console.log('🚀 Starting SupplyNexus Frontend...');
console.log('=====================================');

// 显示环境变量信息
function showEnvironmentInfo() {
  console.log('🌍 Frontend Environment Configuration:');
  console.log('=====================================');

  // 检查不同的环境文件
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
}

// 显示环境信息
showEnvironmentInfo();

// 启动 Next.js 开发服务器
console.log('🚀 Starting Next.js development server...');
console.log('=====================================');

const nextProcess = spawn('npx', ['next', 'dev'], {
  stdio: 'inherit',
  shell: true,
  env: {
    ...process.env,
    FORCE_COLOR: '1'
  }
});

nextProcess.on('error', (error) => {
  console.error('❌ Failed to start Next.js:', error);
  process.exit(1);
});

nextProcess.on('close', (code) => {
  console.log(`\n🏁 Next.js process exited with code ${code}`);
  process.exit(code);
});

// 处理进程退出
process.on('SIGINT', () => {
  console.log('\n🛑 Received SIGINT, shutting down...');
  nextProcess.kill('SIGINT');
});

process.on('SIGTERM', () => {
  console.log('\n🛑 Received SIGTERM, shutting down...');
  nextProcess.kill('SIGTERM');
});
