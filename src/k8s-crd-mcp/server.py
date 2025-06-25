from typing import Dict, List
from fastmcp import FastMCP
from kube_utils import  get_kube_extensionsv1_client, get_kube_dynamic_client
from mcp_tools.create import add_create_tool
from mcp_tools.docs import add_doc
from mcp_tools.list import add_list_tool
from mcp_tools.update import add_update_tool
from mcp_tools.get import add_get_tool
import logging
import sys

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    stream=sys.stdout
)

mcp_server = FastMCP()

@mcp_server.resource("docs://cluster-provision-instructions")
def prompt_cluster_provision_instructions():
    """
    Returns instructions for OpenShiftcluster provisioning with Assisted Installer
    """
    return """
    When provisioning a cluster, you can follow this guide: https://github.com/openshift/assisted-service/blob/master/docs/hive-integration/README.md
    You can also use create_<crd_name> tool to create the resources, and update_<crd_name> tool to update the resources.

    Pullsecret and ssh public key will be provided to you: pull-secret in the form of already created secret (you will not need to know it)
    and public key will be provided to you by the user. Prompt the user to do so.
    """


def add_k8s_resources(mcp: FastMCP, groups: List[str], allowed_crds: Dict[str, List[str]]):
    """
    Adds Kubernetes resources to the MCP server based on the provided groups.
    """
    extensions_v1 = get_kube_extensionsv1_client()
    k8s_client = get_kube_dynamic_client()

    crd_list = extensions_v1.list_custom_resource_definition()
    for crd in crd_list.items:
        if crd.metadata.name not in allowed_crds.keys():
            #logging.info(f"Skipping CRD {crd.metadata.name}")
            continue
        if crd.spec.group not in groups:
            #logging.info(f"Skipping CRD {crd.metadata.name}")
            continue
        logging.info(f"Adding CRD {crd.metadata.name}")
        
        if "docs" in allowed_crds[crd.metadata.name]:
            logging.info(f"Adding docs tool for {crd.metadata.name}")
            add_doc(mcp, crd)
        if "list" in allowed_crds[crd.metadata.name]:
            logging.info(f"Adding list tool for {crd.metadata.name}")
            add_list_tool(mcp, crd)
        if "get" in allowed_crds[crd.metadata.name]:
            logging.info(f"Adding get tool fo {crd.metadata.name}")
            add_get_tool(mcp, crd)
        if "create" in allowed_crds[crd.metadata.name]:
            logging.info(f"Adding create tool for {crd.metadata.name}")
            add_create_tool(mcp, crd)
        if "update" in allowed_crds[crd.metadata.name]:
            logging.info(f"Adding update tool for {crd.metadata.name}")
            add_update_tool(mcp, crd)




if __name__ == "__main__":
    logging.info("Starting k8s-crd MCP Server...")
    allowed_crds = {
        "agentclusterinstalls.extensions.hive.openshift.io": ["create", "get", "update"],
        "agents.agent-install.openshift.io": ["list", "get", "update"],
        #("agentserviceconfigs.agent-install.openshift.io", ["create", "get", "update"]),
        "clusterdeployments.hive.openshift.io": ["create", "get", "update"],
        "clusterimagesets.hive.openshift.io": ["create", "get"],
        "infraenvs.agent-install.openshift.io": ["create", "get", "update"],
        "nmstateconfigs.agent-install.openshift.io": ["create", "get", "update"],
    }
    add_k8s_resources(mcp_server, ["agent-install.openshift.io", "extensions.hive.openshift.io", "hive.openshift.io"], allowed_crds)
    logging.info("Starting MCP server on port 8080...")
    mcp_server.run(transport="sse", host="127.0.0.1", port=8000)