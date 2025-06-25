from fastmcp import FastMCP
from fastmcp.tools import FunctionTool

from .utils import filter_properties, update_unstructured_object


def get_cluster_update_function(crd):
    def update_function(name: str, **kwargs):
        """
        Update a cluster-scoped resource of a specific kind.

        Args:
            name (str): The name of the resource to update.
            **kwargs: Additional properties to set in the resource spec.

        Returns:
            dict: The updated resource object.
        """
        group = crd.spec.group
        version = crd.spec.versions[0].name
        kind = crd.spec.names.kind
        plural = crd.spec.names.plural
        unstructured_object_body = {
            "apiVersion": f"{group}/{version}",
            "kind": kind,
            "metadata": {
                "name": name,
            },
            "spec": kwargs
        }
        return update_unstructured_object(group, version, kind, plural, unstructured_object_body)
    return update_function

def get_namespaced_update_function(crd):
    def update_function(name: str, namespace: str, **kwargs):
        """
        Update a namespaced resource of a specific kind.

        Args:
            name (str): The name of the resource to update.
            namespace (str): The namespace where the resource will be updated.
            **kwargs: Additional properties to set in the resource spec.

        Returns:
            dict: The updated resource object.
        """
        group = crd.spec.group
        version = crd.spec.versions[0].name
        kind = crd.spec.names.kind
        plural = crd.spec.names.plural

        unstructured_object_body = {
            "apiVersion": f"{group}/{version}",
            "kind": kind,
            "metadata": {
                "name": name,
                "namespace": namespace
            },
            "spec": kwargs
        }
        return update_unstructured_object(group, version, kind, plural, unstructured_object_body)
    return update_function


def add_update_tool(mcp_server: FastMCP, crd):
    crd_schema = crd.spec.versions[0].schema.open_apiv3_schema
    scope = crd.spec.scope
    params = filter_properties(crd_schema.properties['spec'].to_dict(), remove_props=["required"])
    params['properties']['name'] = {
        "type": "string",
        "description": "The name of the resource to update"
    }
    if scope == "Namespaced":
        params['properties']['namespace'] = {
            "type": "string",
            "description": "The namespace of the resource to update"
        }
        fn = get_namespaced_update_function(crd)
    else:
        fn = get_cluster_update_function(crd)

    t = FunctionTool(
        name="update_" + crd.spec.names.kind.lower(),
        parameters=params,
        description=f"Update {crd.spec.names.kind} resource",
        fn=fn,
    )
    mcp_server.add_tool(t) 