import logging
from fastmcp import FastMCP
from fastmcp.tools import FunctionTool

from kube_utils import get_kube_custom_objects_client


def get_cluster_list_function(crd):
    def list_function(namespace: str):
        """
        List all cluster-scoped resources of a specific kind

        Returns:
            List[str]: A list of resource objects.
        """
        k8s_client = get_kube_custom_objects_client()
        group = crd.spec.group
        version = crd.spec.versions[0].name
        kind = crd.spec.names.kind
        plural = crd.spec.names.plural

        crd_list = k8s_client.list_cluster_custom_object(
            group=group,
            version=version,
            plural=plural
        )
        logging.info(f"Listed {len(crd_list.get('items', []))} {kind} resources in cluster")
        if 'items' not in crd_list:
            logging.warning(f"No items found in namespace {namespace} for {kind}")
            return []
        return [item['metadata']['name'] for item in crd_list['items']]
    return list_function

def get_namespaced_list_function(crd):
    def list_function(namespace: str):
        """
        List all resources of a specific kind in a given namespace.

        Args:
            namespace (str): The namespace to list resources from.

        Returns:
            List[str]: A list of resource objects.
        """
        k8s_client = get_kube_custom_objects_client()
        group = crd.spec.group
        version = crd.spec.versions[0].name
        kind = crd.spec.names.kind
        plural = crd.spec.names.plural

        crd_list = k8s_client.list_namespaced_custom_object(
            group=group,
            version=version,
            namespace=namespace,
            plural=plural
        )
        logging.info(f"Listed {len(crd_list.get('items', []))} {kind} resources in namespace {namespace}")
        if 'items' not in crd_list:
            logging.warning(f"No items found in namespace {namespace} for {kind}")
            return []
        return [item['metadata']['name'] for item in crd_list['items']]
    return list_function

def add_list_tool(mcp_server: FastMCP, crd):
    crd_schema = crd.spec.versions[0].schema.open_apiv3_schema
    scope = crd.spec.scope
    if scope == "Namespaced":
        params = {
            "type": "object",
            "properties": {
                "namespace": {
                    "type": "string",
                    "description": "The namespace to list resources from"
                }
            },
            "required": ["namespace"]
        }
        fn = get_namespaced_list_function(crd)
    else:
        params = {}
        fn = get_cluster_list_function(crd)

    t = FunctionTool(
        name="list_" + crd.spec.names.kind.lower(),
        parameters=params,
        description=f"List all {crd.spec.names.kind} resources. This is a desc",
        fn=fn,
    )
    mcp_server.add_tool(t) 