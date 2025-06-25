from typing import Dict, List, Optional
from fastmcp import FastMCP
from kube_utils import  get_kube_extensionsv1_client, get_kube_dynamic_client
from mcp_tools.create import add_create_tool
from mcp_tools.docs import add_doc
from mcp_tools.list import add_list_tool
from mcp_tools.update import add_update_tool
from mcp_tools.get import add_get_tool
import logging
import sys
import argparse
import yaml
from pathlib import Path

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


def load_config_from_yaml(config_file: str) -> tuple[Dict[str, List[str]], Dict[str, List[str]]]:
    """
    Load allowed CRDs and groups configuration from YAML file.
    
    Args:
        config_file: Path to the YAML configuration file
        
    Returns:
        Tuple of (allowed_crds, allowed_groups) dictionaries.
        Empty dictionaries mean allow all CRDs/groups with all methods.
    """
    try:
        with open(config_file, 'r') as f:
            config = yaml.safe_load(f)
        
        # Handle empty file or None content
        if not config:
            logging.info(f"Empty configuration file {config_file} - allowing all CRDs with all methods")
            return {}, {}
        
        # Process allowed_crds
        allowed_crds = {}
        crd_list = config.get('allowed_crds', [])
        
        for crd_config in crd_list:
            crd_name = crd_config.get('name')
            methods = crd_config.get('methods', [])
            if crd_name:
                # Empty methods list means allow all methods for this CRD
                if not methods:
                    logging.info(f"Empty methods list for CRD {crd_name} - allowing all methods")
                    methods = ['docs', 'list', 'get', 'create', 'update']
                allowed_crds[crd_name] = methods
        
        # Process allowed_groups
        allowed_groups = {}
        group_list = config.get('allowed_groups', [])
        
        for group_config in group_list:
            group_name = group_config.get('name')
            methods = group_config.get('methods', [])
            if group_name:
                # Empty methods list means allow all methods for this group
                if not methods:
                    logging.info(f"Empty methods list for group {group_name} - allowing all methods")
                    methods = ['docs', 'list', 'get', 'create', 'update']
                allowed_groups[group_name] = methods
        
        # Handle case where both lists are empty
        if not crd_list and not group_list:
            logging.info(f"Empty allowed_crds and allowed_groups lists in {config_file} - allowing all CRDs with all methods")
            return {}, {}
                
        logging.info(f"Loaded configuration: {len(allowed_crds)} CRDs, {len(allowed_groups)} groups from {config_file}")
        return allowed_crds, allowed_groups
        
    except FileNotFoundError:
        logging.error(f"Configuration file {config_file} not found")
        sys.exit(1)
    except yaml.YAMLError as e:
        logging.error(f"Error parsing YAML file {config_file}: {e}")
        sys.exit(1)
    except Exception as e:
        logging.error(f"Error loading configuration: {e}")
        sys.exit(1)


def get_default_config() -> tuple[Dict[str, List[str]], Dict[str, List[str]]]:
    """
    Returns the default hardcoded configuration.
    """
    allowed_crds = {
        "agentclusterinstalls.extensions.hive.openshift.io": ["create", "get", "update"],
        "agents.agent-install.openshift.io": ["list", "get", "update"],
        "clusterdeployments.hive.openshift.io": ["create", "get", "update"],
        "clusterimagesets.hive.openshift.io": ["create", "get"],
        "infraenvs.agent-install.openshift.io": ["create", "get", "update"],
        "nmstateconfigs.agent-install.openshift.io": ["create", "get", "update"],
    }
    allowed_groups = {}
    return allowed_crds, allowed_groups


def get_effective_methods(crd_name: str, crd_group: str, allowed_crds: Dict[str, List[str]], allowed_groups: Dict[str, List[str]]) -> List[str]:
    """
    Get the effective methods for a CRD based on individual CRD config and group config.
    Individual CRD configuration takes precedence over group configuration.
    
    Args:
        crd_name: Name of the CRD
        crd_group: Group of the CRD
        allowed_crds: Dictionary of allowed CRDs and their methods
        allowed_groups: Dictionary of allowed groups and their methods
        
    Returns:
        List of allowed methods for this CRD, or empty list if not allowed
    """
    # Check if CRD is explicitly configured (takes precedence)
    if crd_name in allowed_crds:
        return allowed_crds[crd_name]
    
    # Check if group is configured
    if crd_group in allowed_groups:
        return allowed_groups[crd_group]
    
    # If both allowed_crds and allowed_groups are empty, allow all
    if len(allowed_crds) == 0 and len(allowed_groups) == 0:
        return ['docs', 'list', 'get', 'create', 'update']
    
    # Not explicitly allowed
    return []


def add_k8s_resources(mcp: FastMCP, allowed_crds: Dict[str, List[str]], allowed_groups: Optional[Dict[str, List[str]]] = None):
    """
    Adds Kubernetes resources to the MCP server based on the provided configuration.
    
    Args:
        mcp: FastMCP server instance
        allowed_crds: Dictionary mapping CRD names to allowed methods
        allowed_groups: Dictionary mapping group names to allowed methods
    """
    if allowed_groups is None:
        allowed_groups = {}
        
    extensions_v1 = get_kube_extensionsv1_client()

    logging.info(f"Adding CRDs from extensions_v1")
    crd_list = extensions_v1.list_custom_resource_definition()
    for crd in crd_list.items:
        logging.info(f"Adding CRD {crd.metadata.name} (group: {crd.spec.group})")
        crd_name = crd.metadata.name
        crd_group = crd.spec.group
        
        # Get effective methods for this CRD
        allowed_methods = get_effective_methods(crd_name, crd_group, allowed_crds, allowed_groups)
        
        # Skip if no methods are allowed
        if not allowed_methods:
            continue
            
        logging.info(f"Adding CRD {crd_name} (group: {crd_group}) with methods: {allowed_methods}")
        
        if "docs" in allowed_methods:
            logging.info(f"Adding docs tool for {crd_name}")
            add_doc(mcp, crd)
        if "list" in allowed_methods:
            logging.info(f"Adding list tool for {crd_name}")
            add_list_tool(mcp, crd)
        if "get" in allowed_methods:
            logging.info(f"Adding get tool for {crd_name}")
            add_get_tool(mcp, crd)
        if "create" in allowed_methods:
            logging.info(f"Adding create tool for {crd_name}")
            add_create_tool(mcp, crd)
        if "update" in allowed_methods:
            logging.info(f"Adding update tool for {crd_name}")
            add_update_tool(mcp, crd)


def main():
    parser = argparse.ArgumentParser(description='K8s CRD MCP Server')
    parser.add_argument(
        '--config', 
        type=str, 
        help='Path to YAML configuration file specifying allowed CRDs/groups and methods. Supports both individual CRDs and entire CRD groups. If not provided, uses default configuration.'
    )
    parser.add_argument(
        '--host',
        type=str,
        default='127.0.0.1',
        help='Host to bind the server to (default: 127.0.0.1)'
    )
    parser.add_argument(
        '--port',
        type=int,
        default=8000,
        help='Port to bind the server to (default: 8000)'
    )
    
    args = parser.parse_args()
    
    logging.info("Starting k8s-crd MCP Server...")
    
    # Load configuration
    if args.config:
        allowed_crds, allowed_groups = load_config_from_yaml(args.config)
    else:
        logging.info("No configuration file provided, using default configuration")
        allowed_crds, allowed_groups = get_default_config()
    
    # Add the K8s resources
    add_k8s_resources(mcp_server, allowed_crds, allowed_groups)
    
    logging.info(f"Starting MCP server on {args.host}:{args.port}...")
    mcp_server.run(transport="sse", host=args.host, port=args.port)


if __name__ == "__main__":
    main()