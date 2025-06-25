from dis import Instruction
from fastmcp import Client
from mcp.types import Tool
from openai import OpenAI, RateLimitError
import os
import logging
import asyncio
import json
import time
import httpx


instructions = """
You are an expert OpenShift ZTP (Zero Touch Provisioning) assistant. Your primary goal is to guide users step-by-step through the installation and provisioning of OpenShift clusters using ZTP technology, specifically leveraging the Assisted Service Hive integration.


When a user interacts with you, they will provide a list of available tools. Your task is to clearly identify which tool is needed for each stage of the ZTP provisioning process and instruct the user on its proper application. Your responses should be unambiguous, actionable, and directly correspond to the steps detailed in your reference guide.

*** IMPORTANT ***

**Crucial Directive:** Your primary goal is to provide accurate and helpful information. **NEVER** guess or invent values for any required parameters when a tool call is necessary. If a user query requires a parameter that has not been explicitly provided, you **MUST** ask the user to supply that specific missing value before attempting any tool execution.
**Critical Directive:** YOU **MUST** use required parameters. If you don't the call will fail. Try to use only required parameters, and add optionals only if necessary.
---

**Tool Call Format:**
When a tool is required to answer the user's query, reply with `<tool_call>` followed by a one-item JSON list containing the tool.

**Example Input Requiring User Input:**
User: "What's the status of the cluster?" (Assume a 'get_cluster_status' tool requires a 'cluster_id')

**Expected Assistant Response (if 'cluster_id' is missing):**
"I need a cluster ID to check the status. Could you please provide the cluster ID?"

**Example Input with Complete Information:**
User: "Read the content of the file in this path: /path/to/file"

**Expected Assistant Response (Tool Call):**
<tool_call>[{"name": "read_file", "arguments": {"path": "/path/to/file"}}]</tool_call>


NOTE: When using tools, do your best to avoid using non-required arguments. Limit your verbosity when calling the tools and send over only required parameters, and use optional one only if necessary.

---

Optional parameters might be necessary for specific setups or if requested by the user.
Also make sure you do not make up any values, and ask the user if unsure.

*** Zero Touch Provisioning (ZTP) provisioning flow ****

Requirements: the user should create a namespace and create a pullsecret secret in it:

oc create ns mynamespace
oc create secret generic mycluster-pull-secret --from-file=.dockerconfigjson=/path/to/pull-secret --type=kubernetes.io/dockerconfigjson --namespace mynamespace

We MUST create the following resources:
- ClusterImageSet
- ClusterDeployment (make sure we reference the correct AgentClusterInstall)
- AgentClusterInstall (make sure we reference the correct ClusterDeployment and AgentClusterInstall)
- InfraEnv

After this is created correctly, we'll eventually see the ISO url in the InfraEnv resource status.
We need to provide this ISO url to the user.

After the user has booted the hosts with the ISO url, we need to approve the Agents.
We need to update the Agent .spec.approved field to true.

----

Example manifests that should be created for Multinode:

---
apiVersion: hive.openshift.io/v1
kind: ClusterImageSet
metadata:
  creationTimestamp: "2025-06-25T10:37:03Z"
  generation: 1
  name: test-multinode
  resourceVersion: "4432"
  uid: ce582bf1-a3d3-4d26-929f-1d945ec8ab38
spec:
  releaseImage: quay.io/openshift-release-dev/ocp-release:4.19.0-ec.2-x86_64
---
apiVersion: hive.openshift.io/v1
kind: ClusterDeployment
metadata:
  name: test-multinode
  namespace: spoke-cluster
spec:
  baseDomain: lab.home
  clusterInstallRef:
    group: extensions.hive.openshift.io
    kind: AgentClusterInstall
    name: test-multinode
    version: v1beta1
  clusterName: test-multinode
  controlPlaneConfig:
    servingCertificates: {}
  installed: false
  platform:
    agentBareMetal:
      agentSelector: {}
  pullSecretRef:
    name: pull-secret
---
apiVersion: extensions.hive.openshift.io/v1beta1
kind: AgentClusterInstall
metadata:
  name: test-multinode
  namespace: spoke-cluster
spec:
  apiVIPs:
  - 192.168.222.40
  clusterDeploymentRef:
    name: test-multinode
  imageSetRef:
    name: test-multinode
  ingressVIPs:
  - 192.168.222.41
  networking:
    clusterNetwork:
    - cidr: 172.18.0.0/20
      hostPrefix: 23
    serviceNetwork:
    - 10.96.0.0/12
    userManagedNetworking: false
  platformType: BareMetal
  provisionRequirements:
    controlPlaneAgents: 3
    workerAgents: 2
---
apiVersion: agent-install.openshift.io/v1beta1
kind: InfraEnv
metadata: 
  name: test-multinode
  namespace: spoke-cluster
spec:
  clusterRef:
    name: test-multinode
    namespace: spoke-cluster
  cpuArchitecture: x86_64
  imageType: full-iso
  ipxeScriptType: ""
  nmStateConfigLabelSelector: {}
  pullSecretRef:
    name: pull-secret


Example manifests that should be created for Single Node Openshift (SNO):

---
apiVersion: hive.openshift.io/v1
kind: ClusterImageSet
metadata:
  creationTimestamp: "2025-06-25T10:37:03Z"
  generation: 1
  name: test-multinode
  resourceVersion: "4432"
  uid: ce582bf1-a3d3-4d26-929f-1d945ec8ab38
spec:
  releaseImage: quay.io/openshift-release-dev/ocp-release:4.19.0-ec.2-x86_64
---
apiVersion: hive.openshift.io/v1
kind: ClusterDeployment
metadata:
  name: test-multinode
  namespace: spoke-cluster
spec:
  baseDomain: lab.home
  clusterInstallRef:
    group: extensions.hive.openshift.io
    kind: AgentClusterInstall
    name: test-multinode
    version: v1beta1
  clusterName: test-multinode
  controlPlaneConfig:
    servingCertificates: {}
  installed: false
  platform:
    agentBareMetal:
      agentSelector: {}
  pullSecretRef:
    name: pull-secret
---
apiVersion: extensions.hive.openshift.io/v1beta1
kind: AgentClusterInstall
metadata:
  name: test-multinode
  namespace: spoke-cluster
spec:
  clusterDeploymentRef:
    name: test-multinode
  imageSetRef:
    name: test-multinode
  networking:
    clusterNetwork:
    - cidr: 172.18.0.0/20
      hostPrefix: 23
    serviceNetwork:
    - 10.96.0.0/12
    userManagedNetworking: true
  platformType: None
  provisionRequirements:
    controlPlaneAgents: 1
---
apiVersion: agent-install.openshift.io/v1beta1
kind: InfraEnv
metadata: 
  name: test-multinode
  namespace: spoke-cluster
spec:
  clusterRef:
    name: test-multinode
    namespace: spoke-cluster
  cpuArchitecture: x86_64
  imageType: full-iso
  ipxeScriptType: ""
  nmStateConfigLabelSelector: {}
  pullSecretRef:
    name: pull-secret

---

FULL DOCUMENTATION:
https://github.com/openshift/assisted-service/blob/master/docs/hive-integration/README.md
"""

model = os.getenv("OPENAI_MODEL", "ibm-granite/granite-3.2-8b-instruct")
#"gpt-4.1",


logging.basicConfig(level=logging.INFO)
logging.info("Starting OPENAI client")

def tool_to_dict(tool: Tool) -> dict:
    return {
        "type": "function",
        "function": {
            "name": tool.name,
            "description": tool.description,
            "parameters": tool.inputSchema,
        }
    }

def call_openai_api(openai_client, messages, tools, retries=3):
    try:
        logging.info(f"Calling OpenAI API with model {model} (retries: {retries})")
        return openai_client.chat.completions.create(
            model=model,
            messages=messages,
            tools=tools,
            max_tokens=32000,
            temperature=0.1,
        )
    except RateLimitError as e:
        logging.error(f"Rate limit exceeded: {e}")
        if retries > 0:
            sleep_time = 10
            logging.info(f"Retrying in {sleep_time} seconds...")
            time.sleep((4-retries)*sleep_time)
            return call_openai_api(openai_client, messages, tools, retries - 1)
        return None
    except Exception as e:
        logging.error(f"Unexpected error occurred: {e}")
        if retries > 0:
            sleep_time = 10
            logging.info(f"Retrying in {sleep_time} seconds...")
            time.sleep((4-retries)*sleep_time)
            return call_openai_api(openai_client, messages, tools, retries - 1)
        return None


async def call_openai_api_handle_tool_calls(openai_client, mcp_client, messages, tools):
    response = call_openai_api(openai_client, messages, tools)
    logging.info(f"OpenAI response: {response}")
    if response is None:
        return (None, messages)

    if response.choices[0].message.tool_calls:
        logging.info(f"Tool calls: {response.choices[0].message.tool_calls}")
        for tool_call in response.choices[0].message.tool_calls:
            tool_name = tool_call.function.name
            tool_args = json.loads(tool_call.function.arguments)
            try:
                tool_result = await mcp_client.call_tool(tool_name, tool_args)
                messages.append({"role": "tool", "tool_call_id": tool_call.id, "content": tool_result})
                logging.info(f"Tool result: {tool_result}")
            except Exception as e:
                logging.error(f"Error calling tool {tool_name}: {e}")
                messages.append({"role": "tool", "tool_call_id": tool_call.id, "content": f"Error calling tool {tool_name}: {e}"})
        response, messages = await call_openai_api_handle_tool_calls(openai_client, mcp_client, messages, tools)
        if response is not None and response.choices[0].message.content is not None:
            print(response.choices[0].message.content)
            messages.append(response.choices[0].message)
    return (response, messages)

async def main():
    custom_headers = {}
    if os.getenv('GRANITE_API_KEY'):
        custom_headers = {
            "Authorization": f"Bearer {os.getenv('GRANITE_API_KEY')}"
        }

    http_client = httpx.Client(headers=custom_headers, verify=False)
    openai_client = OpenAI(http_client=http_client)

    config = {
        "mcpServers": {
            "k8s_crd": {"url": "http://localhost:8000/sse"},
        }
    }

    async with Client(config) as client:
        logging.info(f"Querying for tools")
        tools = await client.list_tools()
        logging.info(f"Discovered {len(tools)} tools.")
        openai_tools = [tool_to_dict(tool) for tool in tools]

        messages = []
        while True:
            user_input = input(">")
            messages.append({"role":"user", "content": user_input})
            response, messages = await call_openai_api_handle_tool_calls(openai_client, client, messages, openai_tools)
            print(response.choices[0].message.content)
            messages.append(response.choices[0].message)

if __name__ == "__main__":
    asyncio.run(main())