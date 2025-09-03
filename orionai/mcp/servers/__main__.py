#!/usr/bin/env python3
"""
MCP Calculator Server Entry Point
================================

Entry point for running the calculator MCP server.
"""

if __name__ == "__main__":
    from orionai.mcp.servers.calculator import main
    import asyncio
    asyncio.run(main())
