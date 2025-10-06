#!/usr/bin/env python3
"""FastMCP client to test the deployed basic-agent server."""

import os
import sys
import asyncio
import json
from fastmcp import Client

mcpac_api_key = os.environ.get("MCPAC_API_KEY")

async def main():
    """Connect to MCP server and test the example_usage tool."""
    
    # Get the app URL from environment or command line
    server_url = os.environ.get("MCP_APP_URL")
    if not server_url and len(sys.argv) > 1:
        server_url = sys.argv[1]
    
    if not server_url:
        print("❌ No MCP_APP_URL provided")
        print("Usage: MCP_APP_URL=https://... python client.py")
        print("   or: python client.py https://...")
        return 1
    
    print(f"🔌 Connecting to MCP server at: {server_url}")
    
    # Create configuration for the MCP server
    config = {
        "mcpServers": {
            "basic_agent": {
                "transport": "sse",  # Use SSE transport for mcp-agent deployments
                "url": server_url + "/sse",
                "headers": {
                    "Authorization": "Bearer " + mcpac_api_key
                }
            }
        }
    }
    
    # Create FastMCP client with configuration
    client = Client(config)
    
    try:
        async with client:
            # Test connection
            print("🏓 Testing connection...")
            await client.ping()
            print("✅ Connected successfully!")
            
            # List available operations
            print("\n📋 Listing available operations...")
            tools = await client.list_tools()
            resources = await client.list_resources()
            prompts = await client.list_prompts()
            
            # Print available tools
            if tools:
                print("\nAvailable tools:")
                for tool in tools:
                    print(f" * {tool.name}: {tool.description}")
            else:
                print("No tools available")
            
            # Print available resources
            if resources:
                print("\nAvailable resources:")
                for resource in resources:
                    print(f" * {resource.name}: {resource.description if hasattr(resource, 'description') else 'N/A'}")
            
            # Print available prompts
            if prompts:
                print("\nAvailable prompts:")
                for prompt in prompts:
                    print(f" * {prompt.name}: {prompt.description if hasattr(prompt, 'description') else 'N/A'}")
            
            # Check if example_usage tool exists
            tool_names = [tool.name for tool in tools] if tools else []
            
            if "example_usage" in tool_names:
                print("\n🔧 Calling example_usage tool...")
                try:
                    result = await client.call_tool("example_usage", {})
                    
                    print(f"📤 Response received")
                    
                    # Handle different response types
                    if isinstance(result, str):
                        print(f"📝 String response: {result[:500]}...")  # First 500 chars
                        try:
                            response_data = json.loads(result)
                            print(f"📊 Parsed JSON: {json.dumps(response_data, indent=2)[:500]}...")
                        except json.JSONDecodeError:
                            pass
                    elif isinstance(result, dict):
                        print(f"📊 Dictionary response: {json.dumps(result, indent=2)[:500]}...")
                    else:
                        print(f"📤 Response type: {type(result)}")
                        print(f"📤 Response: {str(result)[:500]}...")
                    
                    print("✅ Tool call completed successfully!")
                    return 0
                except Exception as e:
                    print(f"❌ Error calling tool: {e}")
                    return 1
            else:
                print("❌ example_usage tool not found")
                print(f"Available tools: {tool_names}")
                
                # If no example_usage, try to call any available tool as a test
                if tool_names:
                    first_tool = tool_names[0]
                    print(f"\n🔧 Trying first available tool: {first_tool}...")
                    try:
                        # Get tool details
                        tool_obj = next((t for t in tools if t.name == first_tool), None)
                        if tool_obj and hasattr(tool_obj, 'inputSchema'):
                            print(f"📋 Tool input schema: {tool_obj.inputSchema}")
                        
                        result = await client.call_tool(first_tool, {})
                        print(f"📤 Response: {str(result)[:500]}...")
                        print("✅ Tool call completed!")
                        return 0
                    except Exception as e:
                        print(f"⚠️ Tool call failed (might need arguments): {e}")
                        return 1
                else:
                    print("⚠️ No tools available to test")
                    return 1

    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    exit(exit_code)
