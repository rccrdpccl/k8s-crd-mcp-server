from typing import Dict

from kube_utils import get_kube_custom_objects_client, get_kube_dynamic_client


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
        if key in ["type", "description", "required", "items"] and key not in remove_props:
            if key in properties and properties[key] is not None:
                filtered_properties[key] = properties[key]
                if key == "description":
                    filtered_properties[key] = properties[key][:100]

    if "properties" in properties and properties["properties"] is not None:
        filtered_properties["properties"] = {}
        for key, prop in properties["properties"].items():
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
    try:
        if 'namespace' in unstructured_object_body['metadata'].keys():
            namespace = unstructured_object_body['metadata']['namespace']
            created_object = api_client.create_namespaced_custom_object(group=group, version=version, plural=plural, namespace=namespace, body=unstructured_object_body)
        else:
            created_object = api_client.create_cluster_custom_object(group=group, version=version, plural=plural, body=unstructured_object_body)
        if created_object:
            return {"success": True}
        else:
            return {"success": False, "error": "Failed to create resource"}
    except Exception as e:
        return {"success": False, "error": f"Failed to create resource {kind}: {str(e)}"}


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
    api_resource = api_client.resources.get(api_version=f"{group}/{version}", kind=kind)
    try:
        if 'namespace' in unstructured_object_body['metadata'].keys():
            api_resource.patch(
                body=unstructured_object_body,
                name=unstructured_object_body['metadata']['name'],
                namespace=unstructured_object_body['metadata']['namespace'],
                content_type="application/strategic-merge-patch+json"
            )
            return {"success": True}
        else:
            api_resource.patch(
                body=unstructured_object_body,
                name=unstructured_object_body['metadata']['name'],
                content_type="application/strategic-merge-patch+json"
            )
        return {"success": True}
    except Exception as e:
        return {"success": False, "error": f"Failed to update resource {kind}: {str(e)}"} 