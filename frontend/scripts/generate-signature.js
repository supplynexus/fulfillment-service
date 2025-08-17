#!/usr/bin/env node
/**
 * Signature Generator Script for Testing
 * 用于测试的签名生成脚本
 */

const crypto = require('crypto');
const fs = require('fs');
const path = require('path');

// Load environment variables from .env.local if exists
const envPath = path.join(__dirname, '../.env.local');
if (fs.existsSync(envPath)) {
  const envContent = fs.readFileSync(envPath, 'utf8');
  envContent.split('\n').forEach(line => {
    const [key, ...valueParts] = line.split('=');
    if (key && valueParts.length > 0) {
      process.env[key.trim()] = valueParts.join('=').trim();
    }
  });
}

class SignatureGenerator {
  constructor(privateKey, keyId = 'frontend-server-1') {
    this.privateKey = privateKey;
    this.keyId = keyId;
  }

  createSignatureString(method, path, timestamp, nonce, user_id, body = "") {
    const userPart = user_id ? `${user_id}` : "";
    return `${method.toUpperCase()}${path}${timestamp}${nonce}${userPart}${body}`;
  }

  signData(data) {
    const sign = crypto.createSign('RSA-SHA256');
    sign.update(data);
    return sign.sign(this.privateKey, 'hex');
  }

  generateSignature(options) {
    const {
      method,
      path,
      body = "",
      user_id,
      timestamp = Math.floor(Date.now() / 1000),
      nonce = crypto.randomBytes(16).toString('hex'),
      key_id = this.keyId
    } = options;

    // Create signature string
    const signatureString = this.createSignatureString(
      method,
      path,
      timestamp,
      nonce,
      user_id,
      body
    );

    // Sign the data
    const signature = this.signData(signatureString);

    // Create signature data structure
    const signatureData = {
      timestamp,
      nonce,
      user_id,
      signature,
      key_id
    };

    // Encode to base64
    return Buffer.from(JSON.stringify(signatureData)).toString('base64');
  }

  generateHeaders(options) {
    const signature = this.generateSignature(options);
    
    return {
      'X-Signature': signature,
      'X-Tenant-ID': 'PoRpOk2e', // 硬编码的租户 hashid
      'Content-Type': 'application/json'
    };
  }
}

function main() {
  console.log("=== Frontend Signature Generator ===\n");

  // Check if private key exists
  const privateKeyPath = path.join(__dirname, '../keys/frontend_private_key.pem');
  
  if (!fs.existsSync(privateKeyPath)) {
    console.error(`❌ Private key not found at: ${privateKeyPath}`);
    console.log("\nPlease generate the private key first:");
    console.log("cd frontend/keys");
    console.log("openssl genrsa -out frontend_private_key.pem 2048");
    console.log("openssl rsa -in frontend_private_key.pem -pubout -out frontend_public_key.pem");
    return;
  }

  // Read private key
  const privateKey = fs.readFileSync(privateKeyPath, 'utf8');
  const generator = new SignatureGenerator(privateKey);

  console.log("✅ Private key loaded successfully");
  console.log(`📁 Key path: ${privateKeyPath}\n`);

  // Generate test signatures
  console.log("🔐 Generating test signatures...\n");

  // 1. Tenant-level API signature
  const tenantSignature = generator.generateSignature({
    method: 'GET',
    path: '/api/v1/orders',
    body: ''
  });

  console.log("1. Tenant-level API signature:");
  console.log(`X-Signature: ${tenantSignature}\n`);

  // 2. User-level API signature
  const userSignature = generator.generateSignature({
    method: 'GET',
    path: '/api/v1/user/profile',
    user_id: 1,
    body: ''
  });

  console.log("2. User-level API signature (user_id=1):");
  console.log(`X-Signature: ${userSignature}\n`);

  // 3. POST request signature
  const postSignature = generator.generateSignature({
    method: 'POST',
    path: '/api/v1/orders',
    body: JSON.stringify({ test: 'data' })
  });

  console.log("3. POST request signature:");
  console.log(`X-Signature: ${postSignature}\n`);

  // Generate curl commands
  console.log("📋 Curl test commands:\n");

  const baseUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

  const tenantHashid = 'PoRpOk2e'; // 硬编码的租户 hashid
  
  console.log("# 1. Test tenant-level API");
  console.log(`curl -X GET '${baseUrl}/api/v1/orders' \\`);
  console.log(`  -H 'X-Tenant-ID: ${tenantHashid}' \\`);
  console.log(`  -H 'X-Signature: ${tenantSignature}'`);
  console.log();

  console.log("# 2. Test user-level API");
  console.log(`curl -X GET '${baseUrl}/api/v1/user/profile' \\`);
  console.log(`  -H 'X-Tenant-ID: ${tenantHashid}' \\`);
  console.log(`  -H 'X-Signature: ${userSignature}'`);
  console.log();

  console.log("# 3. Test POST request");
  console.log(`curl -X POST '${baseUrl}/api/v1/orders' \\`);
  console.log(`  -H 'X-Tenant-ID: ${tenantHashid}' \\`);
  console.log(`  -H 'X-Signature: ${postSignature}' \\`);
  console.log(`  -H 'Content-Type: application/json' \\`);
  console.log(`  -d '{"test": "data"}'`);
  console.log();

  console.log("=== Signature generation completed ===");
}

if (require.main === module) {
  main();
}

module.exports = { SignatureGenerator };
