from typing import Dict
import logging
from kubernetes.client.rest import ApiException

from kube_utils import get_kube_custom_objects_client, get_kube_dynamic_client


def get_preferred_version(crd):
    """
    Get the preferred version for API operations.
    Prefers the storage version, falls back to the first served version.
    
    Args:
        crd: Custom Resource Definition object
        
    Returns:
        str: The preferred version name
    """
    storage_version = None
    served_versions = []
    
    for version in crd.spec.versions:
        if version.served:
            served_versions.append(version)
            if version.storage:
                storage_version = version
    
    if storage_version:
        logging.debug(f"Using storage version {storage_version.name} for CRD {crd.metadata.name}")
        return storage_version.name
    elif served_versions:
        logging.debug(f"Using first served version {served_versions[0].name} for CRD {crd.metadata.name}")
        return served_versions[0].name
    else:
        # Fallback to first version if no served versions found
        fallback_version = crd.spec.versions[0].name
        logging.warning(f"No served versions found for CRD {crd.metadata.name}, using fallback version {fallback_version}")
        return fallback_version


def filter_properties(properties: Dict, remove_props = []) -> Dict:
    """
    Filter properties to only include those that are not read-only.

    Args:
        properties: A dictionary of properties to filter.
        remove_props: A list of property keys to remove.

    Returns:
        A dictionary containing only the writable properties.
    """
    filtered_properties = {}
    for key, prop in properties.items():
        # Hyperthreading is a special case - somehow it's breaking gemini-cli client-side validation @TODO: investigate
        if key == "hyperthreading":
            logging.info(f"Adding hyperthreading: {key}")
        if key == "enum" and prop is not None:
            filtered_properties[key] = list(filter(None, prop))
        if key in ["type", "description", "required", "items", "default"] and key not in remove_props:
            if key in properties and properties[key] is not None:
                if key == "items":
                    filtered_properties[key] = filter_properties(properties[key])
                else:
                    filtered_properties[key] = properties[key]
                if key == "description":
                    filtered_properties[key] = properties[key][:100]

    if "properties" in properties and properties["properties"] is not None:
        filtered_properties["properties"] = {}
        for key, prop in properties["properties"].items():
            # This property is causing issues, @TODO: investigate
            if key not in ["hyperthreading"]:
                filtered_properties["properties"][key] = filter_properties(prop)
    return filtered_properties


def create_unstructured_object(group: str, version: str, kind: str, plural: str, unstructured_object_body: dict):
    """
    Create a Kubernetes custom resource object.

    Args:
        group: The API group of the resource
        version: The API version of the resource  
        kind: The kind of the resource
        plural: The plural name of the resource
        unstructured_object_body: The resource definition

    Returns:
        dict: Success/error status
    """
    api_client = get_kube_custom_objects_client()
    
    # Log detailed information about what we're trying to create
    logging.info(f"Attempting to create resource:")
    logging.info(f"  Group: {group}")
    logging.info(f"  Version: {version}")
    logging.info(f"  Kind: {kind}")
    logging.info(f"  Plural: {plural}")
    logging.info(f"  API Version: {group}/{version}")
    logging.info(f"  Resource body: {unstructured_object_body}")
    
    try:
        if 'namespace' in unstructured_object_body['metadata'].keys():
            namespace = unstructured_object_body['metadata']['namespace']
            logging.info(f"Creating namespaced resource in namespace: {namespace}")
            created_object = api_client.create_namespaced_custom_object(
                group=group, 
                version=version, 
                plural=plural, 
                namespace=namespace, 
                body=unstructured_object_body
            )
            logging.info(f"Successfully created namespaced resource {kind} in namespace {namespace}")
        else:
            logging.info(f"Creating cluster-scoped resource")
            created_object = api_client.create_cluster_custom_object(
                group=group, 
                version=version, 
                plural=plural, 
                body=unstructured_object_body
            )
            logging.info(f"Successfully created cluster-scoped resource {kind}")
        
        if created_object:
            return {"success": True, "resource": created_object}
        else:
            return {"success": False, "error": "Failed to create resource - no response from API"}
            
    except ApiException as e:
        error_details = {
            "status": e.status,
            "reason": e.reason,
            "body": e.body,
            "headers": dict(e.headers) if e.headers else None
        }
        logging.error(f"Kubernetes API error when creating {kind}:")
        logging.error(f"  Status: {e.status}")
        logging.error(f"  Reason: {e.reason}")
        logging.error(f"  Body: {e.body}")
        logging.error(f"  Headers: {e.headers}")
        
        return {
            "success": False, 
            "error": f"Kubernetes API error: {e.reason}",
            "details": error_details,
            "api_error": True
        }
    except Exception as e:
        # Log the full error details
        logging.error(f"Failed to create resource: group: {group}, version: {version}, kind: {kind}, plural: {plural}")
        logging.error(f"Request body: {unstructured_object_body}")
        logging.error(f"Error: {str(e)}")
        logging.error(f"Error type: {type(e)}")
        
        return {
            "success": False, 
            "error": f"Unexpected error creating {kind}: {str(e)}",
            "api_error": False
        }


def update_unstructured_object(group: str, version: str, kind: str, plural: str, unstructured_object_body: dict):
    """
    Update a Kubernetes custom resource object.

    Args:
        group: The API group of the resource
        version: The API version of the resource
        kind: The kind of the resource
        plural: The plural name of the resource
        unstructured_object_body: The resource definition

    Returns:
        dict: Success/error status
    """
    api_client = get_kube_dynamic_client()
    
    logging.info(f"Attempting to update resource:")
    logging.info(f"  Group: {group}")
    logging.info(f"  Version: {version}")
    logging.info(f"  Kind: {kind}")
    logging.info(f"  Resource body: {unstructured_object_body}")
    
    try:
        api_resource = api_client.resources.get(api_version=f"{group}/{version}", kind=kind)
        
        if 'namespace' in unstructured_object_body['metadata'].keys():
            api_resource.patch(
                body=unstructured_object_body,
                name=unstructured_object_body['metadata']['name'],
                namespace=unstructured_object_body['metadata']['namespace'],
                content_type="application/merge-patch+json"
            )
            return {"success": True}
        else:
            api_resource.patch(
                body=unstructured_object_body,
                name=unstructured_object_body['metadata']['name'],
                content_type="application/merge-patch+json"
            )
        return {"success": True}
    except ApiException as e:
        error_details = {
            "status": e.status,
            "reason": e.reason,
            "body": e.body,
            "headers": dict(e.headers) if e.headers else None
        }
        logging.error(f"Kubernetes API error when updating {kind}:")
        logging.error(f"  Status: {e.status}")
        logging.error(f"  Reason: {e.reason}")
        logging.error(f"  Body: {e.body}")
        
        return {
            "success": False, 
            "error": f"Kubernetes API error: {e.reason}",
            "details": error_details,
            "api_error": True
        }
    except Exception as e:
        logging.error(f"Unexpected error when updating {kind}: {str(e)}")
        return {
            "success": False, 
            "error": f"Unexpected error updating {kind}: {str(e)}",
            "api_error": False
        } 