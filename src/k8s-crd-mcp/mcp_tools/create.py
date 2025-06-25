from fastmcp import FastMCP
from fastmcp.tools import FunctionTool
import logging

from .utils import filter_properties, create_unstructured_object, get_preferred_version


def get_cluster_create_function(crd):
    def create_function(name: str, **kwargs):
        """
        Create a cluster-scoped resource of a specific kind.

        Args:
            name (str): The name of the resource to create.
            **kwargs: Additional properties to set in the resource spec.

        Returns:
            dict: The created resource object.
        """
        group = crd.spec.group
        version = get_preferred_version(crd)  # Use preferred version
        kind = crd.spec.names.kind
        plural = crd.spec.names.plural
        
        logging.info(f"Creating {kind} with version {version} (group: {group})")
        
        unstructured_object_body = {
            "apiVersion": f"{group}/{version}",
            "kind": kind,
            "metadata": {
                "name": name,
            },
            "spec": kwargs
        }
        return create_unstructured_object(group, version, kind, plural, unstructured_object_body)
    return create_function

def get_namespaced_create_function(crd):
    def create_function(name: str, namespace: str, **kwargs):
        """
        Create a namespaced resource of a specific kind.

        Args:
            name (str): The name of the resource to create.
            namespace (str): The namespace where the resource will be created.
            **kwargs: Additional properties to set in the resource spec.

        Returns:
            dict: The created resource object.
        """
        group = crd.spec.group
        version = get_preferred_version(crd)  # Use preferred version
        kind = crd.spec.names.kind
        plural = crd.spec.names.plural

        logging.info(f"Creating {kind} with version {version} (group: {group}) in namespace {namespace}")
        
        unstructured_object_body = {
            "apiVersion": f"{group}/{version}",
            "kind": kind,
            "metadata": {
                "name": name,
                "namespace": namespace
            },
            "spec": kwargs
        }
        return create_unstructured_object(group, version, kind, plural, unstructured_object_body)
    return create_function

def add_create_tool(mcp_server: FastMCP, crd):
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
    
    scope = crd.spec.scope
    params = filter_properties(crd_schema.properties['spec'].to_dict())
    params['properties']['name'] = {
        "type": "string",
        "description": "The name of the resource to create"
    }
    if scope == "Namespaced":
        params['properties']['namespace'] = {
            "type": "string",
            "description": "The namespace of the resource to create"
        }
        fn = get_namespaced_create_function(crd)
    else:
        fn = get_cluster_create_function(crd)

    t = FunctionTool(
        name="create_" + crd.spec.names.kind.lower(),
        parameters=params,
        description=f"Create {crd.spec.names.kind} resource",
        fn=fn,
    )
    mcp_server.add_tool(t) 