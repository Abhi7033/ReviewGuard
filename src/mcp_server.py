from mcp.server.mcpserver.server import MCPServer

from .tools import escalate_ticket, lookup_order, search_knowledge_base

mcp = MCPServer("reviewguard")

mcp.tool()(search_knowledge_base)
mcp.tool()(lookup_order)
mcp.tool()(escalate_ticket)

if __name__ == "__main__":
    mcp.run()
