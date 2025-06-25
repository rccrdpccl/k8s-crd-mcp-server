from fastmcp import FastMCP
from fastmcp.tools import FunctionTool
import logging

from .utils import filter_properties, get_preferred_version


def add_doc(mcp_server: FastMCP, crd):
    """
    Add an MCP prompt that documents the tool function created for this CRD
    
    Args:
        mcp: FastMCP server instance
        crd: Custom Resource Definition object
    """
    # Use preferred version for schema selection
    preferred_version = get_preferred_version(crd)
    
    # Find the schema for the preferred version
    crd_schema = None
    for version in crd.spec.versions:
        if version.name == preferred_version:
            crd_schema = version.schema.open_apiv3_schema
            break
    
    # Fallback to first version schema if preferred version schema not found
    if crd_schema is None:
        crd_schema = crd.spec.versions[0].schema.open_apiv3_schema
        logging.warning(f"Could not find schema for preferred version {preferred_version}, using first version")
    
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