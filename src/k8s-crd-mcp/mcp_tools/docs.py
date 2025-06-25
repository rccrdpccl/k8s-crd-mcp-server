from fastmcp import FastMCP
from fastmcp.tools import FunctionTool

from .utils import filter_properties


def add_doc(mcp_server: FastMCP, crd):
    """
    Add an MCP prompt that documents the tool function created for this CRD
    
    Args:
        mcp: FastMCP server instance
        crd: Custom Resource Definition object
    """
    crd_schema = crd.spec.versions[0].schema.open_apiv3_schema
    params = filter_properties(crd_schema.properties['spec'].to_dict())
    params['description'] = crd_schema.description

    def fn():
        return params

    t = FunctionTool(
        name="get_" + crd.spec.names.kind.lower() + "_documentation",
        parameters={},
        description=f"Get full documentation for {crd.spec.names.kind} resource",
        fn=fn,
    )
    mcp_server.add_tool(t) 