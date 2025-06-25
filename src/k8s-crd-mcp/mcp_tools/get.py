from fastmcp import FastMCP
from fastmcp.tools import FunctionTool
import logging

from kube_utils import get_kube_dynamic_client
from .utils import get_preferred_version


def get_cluster_get_function(crd):
    group = crd.spec.group
    version = get_preferred_version(crd)  # Use preferred version
    kind = crd.spec.names.kind
    def get_function(name: str):
        """
        Get a cluster-scoped resource of a specific kind.

        Args:
            name (str): The name of the resource to get.

        Returns:
            dict: The resource object.
        """
        k8s_client = get_kube_dynamic_client()
        api_resource = k8s_client.resources.get(api_version=f"{group}/{version}", kind=f"{kind}")
        res = api_resource.get(name=name)
        return slim(res.to_dict())
    return get_function

def get_namespaced_get_function(crd):
    group = crd.spec.group
    version = get_preferred_version(crd)  # Use preferred version
    kind = crd.spec.names.kind
    def get_function(namespace: str, name: str):
        """
        Get a namespaced resource of a specific kind.

        Args:
            namespace (str): The namespace of the resource to get.
            name (str): The name of the resource to get.

        Returns:
            dict: The resource object.
        """
        k8s_client = get_kube_dynamic_client()
        api_resource = k8s_client.resources.get(api_version=f"{group}/{version}", kind=f"{kind}")
        res = api_resource.get(name=name, namespace=namespace)
        return slim(res.to_dict())
    return get_function

def slim(response):
    del response["metadata"]["managedFields"]
    return response

def add_get_tool(mcp_server: FastMCP, crd):
    scope = crd.spec.scope
    if scope == "Namespaced":
        params = {
            "type": "object",
            "properties": {
                "namespace": {
                    "type": "string",
                    "description": "The namespace to list resources from"
                },
                "name": {
                    "type": "string",
                    "description": "The name of the resource to get"
                }
            },
            "required": ["namespace", "name"]
        }
        fn = get_namespaced_get_function(crd)
    else:
        params = {
            "type": "object",
            "properties": {
                "name": {
                    "type": "string",
                    "description": "The name of the resource to get"
                }
            },
            "required": ["name"]
        }
        fn = get_cluster_get_function(crd)

    t = FunctionTool(
        name="get_" + crd.spec.names.kind.lower(),
        parameters=params,
        description=f"Get {crd.spec.names.kind} resources. This is a desc",
        fn=fn,
    )
    mcp_server.add_tool(t) 