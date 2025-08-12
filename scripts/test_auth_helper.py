#!/usr/bin/env python3
"""
Test authentication helper script
Generates proper authentication headers for testing
"""

import time
import secrets
import hashlib
import argparse
import json
from cryptography.hazmat.primitives import serialization, hashes
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.backends import default_backend


def generate_test_headers(
    method: str,
    path: str,
    body: str = "",
    user_id: int = 1,
    tenant_id: int = 1,
    dev_mode: bool = True
) -> dict:
    """Generate authentication headers for testing"""
    
    if dev_mode:
        # Development mode - simple headers
        return {
            "X-Dev-User-ID": str(user_id),
            "X-Dev-Tenant-ID": str(tenant_id),
            "Content-Type": "application/json"
        }
    else:
        # Production mode - timestamp signature
        return generate_timestamp_signature_headers(
            method, path, body
        )


def generate_timestamp_signature_headers(
    method: str,
    path: str,
    body: str,
    key_id: str = "test_key_123"
) -> dict:
    """Generate timestamp signature headers"""
    
    # Generate timestamp and nonce
    timestamp = int(time.time())
    nonce = secrets.token_urlsafe(32)
    
    # Create signature string
    signature_string = f"{method.upper()}{path}{timestamp}{nonce}{body}"
    
    # For testing, we'll use a simple hash (in real implementation, use private key)
    signature = hashlib.sha256(signature_string.encode()).hexdigest()
    
    return {
        "X-Signature": signature,
        "X-Timestamp": str(timestamp),
        "X-Nonce": nonce,
        "X-Key-ID": key_id,
        "Content-Type": "application/json"
    }


def generate_curl_command(
    method: str,
    url: str,
    headers: dict,
    body: str = ""
) -> str:
    """Generate curl command for testing"""
    
    curl_parts = [f"curl -X {method.upper()} '{url}'"]
    
    # Add headers
    for key, value in headers.items():
        if key != "Content-Type":  # Skip content-type for now
            curl_parts.append(f"  -H '{key}: {value}'")
    
    # Add content-type
    if "Content-Type" in headers:
        curl_parts.append(f"  -H 'Content-Type: {headers['Content-Type']}'")
    
    # Add body if present
    if body:
        curl_parts.append(f"  -d '{body}'")
    
    return " \\\n".join(curl_parts)


def main():
    parser = argparse.ArgumentParser(description="Generate test authentication headers")
    parser.add_argument("--method", default="GET", help="HTTP method")
    parser.add_argument("--path", default="/api/v1/orders", help="API path")
    parser.add_argument("--body", default="", help="Request body")
    parser.add_argument("--user-id", type=int, default=1, help="User ID")
    parser.add_argument("--tenant-id", type=int, default=1, help="Tenant ID")
    parser.add_argument("--dev-mode", action="store_true", default=True, help="Use development mode")
    parser.add_argument("--base-url", default="http://localhost:8000", help="Base URL")
    parser.add_argument("--format", choices=["headers", "curl", "json"], default="headers", help="Output format")
    
    args = parser.parse_args()
    
    # Generate headers
    headers = generate_test_headers(
        method=args.method,
        path=args.path,
        body=args.body,
        user_id=args.user_id,
        tenant_id=args.tenant_id,
        dev_mode=args.dev_mode
    )
    
    # Output in requested format
    if args.format == "headers":
        print("Headers:")
        for key, value in headers.items():
            print(f"{key}: {value}")
    
    elif args.format == "curl":
        url = f"{args.base_url}{args.path}"
        curl_cmd = generate_curl_command(args.method, url, headers, args.body)
        print(curl_cmd)
    
    elif args.format == "json":
        print(json.dumps(headers, indent=2))


if __name__ == "__main__":
    main()
