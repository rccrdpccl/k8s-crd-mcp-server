from kubernetes import config, dynamic, client
from kubernetes.client import api_client

def get_kube_custom_objects_client():
    """
    Returns a Kubernetes client for interacting with custom resources.
    It tries to load the kube config from the local machine first, and if that fails,
    it falls back to loading the in-cluster configuration.
    """
    try:
        config.load_kube_config()
    except config.config_exception.ConfigException:
        config.load_incluster_config()
    return client.CustomObjectsApi()

def get_kube_dynamic_client():
    try:
        c = config.load_kube_config()
    except config.config_exception.ConfigException:
        c = config.load_incluster_config()
    return dynamic.DynamicClient(api_client.ApiClient(configuration=c))

def get_kube_extensionsv1_client():
    try:
        config.load_kube_config()
    except config.config_exception.ConfigException:
        config.load_incluster_config()
    return client.ApiextensionsV1Api()
