---
**Paste this at:** https://github.com/TSavo/printify-mcp/issues/new
**Title:** Use stderr for all logging to fix MCP stdio protocol errors in Cursor
---

> 来源：从 `.cursor/printify-mcp-stdout-issue.md` 迁移。  
> 用途：第三方集成问题记录（长期知识），不属于 agent 运行态文件。

## Summary

When running the server via stdio (e.g. with Cursor or other MCP clients), the client reports many errors like:

```
Client error for command Unexpected token 'P', "Printify A"... is not valid JSON
Client error for command Unexpected token 'S', "Shops response: [" is not valid JSON
Client error for command Unexpected token 'F', "Found 2 shops: [" is not valid JSON
```

The server still connects and lists 19 tools, but the log is noisy and can confuse users.

## Cause

MCP over stdio uses **stdout exclusively for JSON-RPC messages**. Any other output on stdout is read by the client as part of the protocol stream and parsed as JSON, which fails.

This project currently uses `console.log()` (or equivalent) for startup and runtime messages, for example:

- "Printify API ...", "No shop ID ...", "Initializi...", "Fetching s...", "Request: G..."
- "Printify MCP ...", "Printify SDK Error", "Error fetching shops ..."
- "Shops response: [...]", "Found 2 shops: [...]", "Setting de...", "Printify S...", "Shop selec..."
- "REPLICATE_API_TOKEN environment variable is not set. ..."

All of these go to **stdout**, so the MCP client tries to parse them as JSON and reports "is not valid JSON".

## Expected behavior

- **stdout**: Only JSON-RPC messages (as per MCP spec).
- **stderr**: All logging, debug, and error text (e.g. via `console.error()` or a logger that writes to stderr).

## Suggested fix

1. Replace or wrap all `console.log()` used for logging/debug/errors so that output goes to **stderr** (e.g. `console.error()` or a small logger that writes to `process.stderr`).
2. Keep **stdout** strictly for the MCP SDK’s transport (stdio server transport).

Optional: support an env var (e.g. `LOG_LEVEL=silent` or `DEBUG=0`) to reduce or disable log output when running in production MCP clients.

## Environment

- Client: Cursor (MCP stdio)
- Server: `npx -y @tsavo/printify-mcp@latest`
- Node: v18+
- PRINTIFY_API_KEY: set (connection works; "Found 2 shops" appears in logs)

Thank you for maintaining this MCP server.
