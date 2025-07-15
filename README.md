# K8s CRD MCP Server

A Model Context Protocol (MCP) server that dynamically exposes Kubernetes Custom Resource Definitions (CRDs) as MCP tools. This allows AI assistants to interact with Kubernetes clusters through standardized MCP interfaces.

## Features

- **Dynamic CRD Discovery**: Automatically discovers and exposes CRDs from your Kubernetes cluster
- **Configurable Access Control**: Fine-grained control over which CRDs and operations are exposed
- **Multiple Operations**: Supports docs, list, get, create, and update operations for CRDs
- **Flexible Configuration**: YAML-based configuration with support for empty configs (allow all)

## Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd k8s-crd-mcp
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Ensure you have a valid Kubernetes configuration (kubeconfig) set up.

## Configuration

The server uses YAML configuration files to specify which CRDs and operations should be exposed. The configuration supports both individual CRDs and entire CRD groups:

```yaml
allowed_groups:
  - name: <group-name>
    methods:
      - <method1>
      - <method2>
      # ... more methods
  - name: <another-group-name>
    methods:
      - <method1>
      # ... more methods

allowed_crds:
  - name: <crd-name>
    methods:
      - <method1>
      - <method2>
      # ... more methods
  - name: <another-crd-name>
    methods:
      - <method1>
      # ... more methods
```

### Available Methods

- `docs`: Get documentation for the CRD
- `list`: List all resources of this CRD type
- `get`: Get a specific resource by name
- `create`: Create a new resource
- `update`: Update an existing resource

### Configuration Precedence

The server supports both group-based and individual CRD configuration:

1. **Individual CRDs** take precedence over group configuration
2. **Group configuration** applies to all CRDs in that group
3. **Empty methods lists** (`methods: []`) allow all methods
4. **Empty configuration** allows all CRDs with all methods

### Configuration Options

#### 1. Specific Configuration (examples/default_config.yaml)
```yaml
allowed_crds:
  - name: agentclusterinstalls.extensions.hive.openshift.io
    methods:
      - create
      - get
      - update
  - name: agents.agent-install.openshift.io
    methods:
      - list
      - get
      - update
```

#### 2. Read-Only Configuration (examples/readonly_config.yaml)
```yaml
allowed_crds:
  - name: agentclusterinstalls.extensions.hive.openshift.io
    methods:
      - get
  - name: agents.agent-install.openshift.io
    methods:
      - list
      - get
```

#### 3. Full Access Configuration (examples/full_access_config.yaml)
```yaml
allowed_crds:
  - name: agentclusterinstalls.extensions.hive.openshift.io
    methods:
      - docs
      - list
      - get
      - create
      - update
```

#### 4. Allow All Configuration (examples/allow_all_config.yaml)
```yaml
# Empty configuration - allows all CRDs with all methods
allowed_crds: []
```

#### 5. Empty Methods Configuration (examples/empty_methods_config.yaml)
```yaml
allowed_crds:
  - name: agentclusterinstalls.extensions.hive.openshift.io
    methods: []  # Empty methods list allows all methods for this CRD
  - name: agents.agent-install.openshift.io
    methods: []  # Empty methods list allows all methods for this CRD
```

#### 6. Group-Based Configuration (examples/group_based_config.yaml)
```yaml
allowed_groups:
  - name: agent-install.openshift.io
    methods:
      - docs
      - list
      - get
      - create
      - update
  - name: hive.openshift.io
    methods:
      - get
      - create
      - update
```

#### 7. Mixed Configuration (examples/mixed_config.yaml)
```yaml
allowed_groups:
  - name: agent-install.openshift.io
    methods:
      - list
      - get
  - name: hive.openshift.io
    methods:
      - get
      - create
      - update

allowed_crds:
  # Individual CRD config overrides group config
  - name: agents.agent-install.openshift.io
    methods:
      - docs
      - list
      - get
      - create
      - update
  # This CRD gets more restrictive access than its group
  - name: clusterdeployments.hive.openshift.io
    methods:
      - get
```

#### 8. Empty Group Methods Configuration (examples/empty_group_methods_config.yaml)
```yaml
allowed_groups:
  - name: agent-install.openshift.io
    methods: []  # Empty methods list allows all methods for all CRDs in this group
  - name: hive.openshift.io
    methods: []  # Empty methods list allows all methods for all CRDs in this group

allowed_crds:
  # Individual CRD can still override group settings
  - name: clusterdeployments.hive.openshift.io
    methods:
      - get  # Only get method for this specific CRD
```

### Configuration Rules

- **Empty file or empty `allowed_crds` and `allowed_groups` lists**: Allows all CRDs with all methods
- **Empty `methods` list for a CRD**: Allows all methods for that specific CRD
- **Empty `methods` list for a group**: Allows all methods for all CRDs in that group
- **Individual CRD configuration**: Takes precedence over group configuration
- **Group configuration**: Applies to all CRDs in that group (unless overridden by individual CRD config)
- **No configuration file provided**: Uses default hardcoded configuration

## Usage

### Running the Server

#### Basic Usage
```bash
cd src/k8s-crd-mcp
python server.py --config ../../examples/default_config.yaml
```

#### With Custom Host and Port
```bash
python server.py --config ../../examples/default_config.yaml --host 0.0.0.0 --port 8080
```

#### Using Default Configuration (No Config File)
```bash
python server.py
```

#### Allow All CRDs and Methods
```bash
python server.py --config ../../examples/allow_all_config.yaml
```

#### Group-Based Configuration
```bash
# Allow all operations for specific groups
python server.py --config ../../examples/group_based_config.yaml

# Mixed group and individual CRD configuration
python server.py --config ../../examples/mixed_config.yaml

# Empty methods for groups (allows all methods for all CRDs in those groups)
python server.py --config ../../examples/empty_group_methods_config.yaml
```

### Command Line Options

- `--config`: Path to YAML configuration file (optional)
- `--host`: Host to bind the server to (default: 127.0.0.1)
- `--port`: Port to bind the server to (default: 8000)

### Using the MCP Client

The repository includes a client for testing and interaction:

```bash
cd src/k8s-crd-mcp
python client.py
```

The client provides:
- Interactive tool discovery
- Tool execution with parameter input
- Async operation support
- Error handling and logging

## Example Workflows

### OpenShift Cluster Provisioning

1. **Start the server with cluster provisioning CRDs**:
```bash
python server.py --config ../../examples/default_config.yaml
```

2. **Create ClusterDeployment**:
```bash
# The server exposes mcp_k8s-crd-mcp_create_clusterdeployment tool
# Use with your MCP client to create cluster deployments
```

3. **Create AgentClusterInstall**:
```bash
# The server exposes mcp_k8s-crd-mcp_create_agentclusterinstall tool
# Use with your MCP client to configure cluster installation
```

### Read-Only Operations

1. **Start server in read-only mode**:
```bash
python server.py --config ../../examples/readonly_config.yaml
```

2. **List and inspect resources**:
```bash
# Only list and get operations are available
# Create and update operations are not exposed
```

## API Reference

### Tool Naming Convention

Tools are named following the pattern: `mcp_k8s-crd-mcp_<operation>_<crd_simple_name>`

Examples:
- `mcp_k8s-crd-mcp_create_agentclusterinstall`
- `mcp_k8s-crd-mcp_get_agent`
- `mcp_k8s-crd-mcp_list_clusterdeployment`

### Resource Parameters

#### Create/Update Operations
- `name`: Resource name
- `namespace`: Kubernetes namespace
- Additional parameters based on the CRD specification

#### Get Operations
- `name`: Resource name
- `namespace`: Kubernetes namespace

#### List Operations
- `namespace`: Kubernetes namespace

### Error Handling

The server includes comprehensive error handling:
- Kubernetes API errors
- Configuration validation errors
- Resource not found errors
- Permission errors

## Development

### Project Structure

```
k8s-crd-mcp/
├── src/k8s-crd-mcp/
│   ├── server.py           # Main MCP server
│   ├── client.py           # MCP client for testing
│   ├── kube_utils.py       # Kubernetes utilities
│   └── mcp_tools/          # MCP tool implementations
│       ├── create.py       # Create operations
│       ├── get.py          # Get operations
│       ├── list.py         # List operations
│       ├── update.py       # Update operations
│       ├── docs.py         # Documentation operations
│       └── utils.py        # Utility functions
├── examples/               # Configuration examples
├── requirements.txt        # Python dependencies
└── README.md              # This file
```

### Adding New CRDs

To add support for new CRDs:

1. **Update your configuration file** to include the new CRD or its group:
```yaml
# Option 1: Add individual CRD
allowed_crds:
  - name: your.new.crd.name
    methods:
      - get
      - create
      - update

# Option 2: Add entire group (easier for multiple CRDs)
allowed_groups:
  - name: your.new.group.name
    methods:
      - get
      - create
      - update
```

2. **Restart the server** - CRDs are discovered dynamically at startup

### Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## Troubleshooting

### Common Issues

1. **"CRD not found"**: Ensure the CRD is installed in your cluster
2. **"Permission denied"**: Check your kubeconfig permissions
3. **"Configuration file not found"**: Verify the path to your config file
4. **"Port already in use"**: Change the port using `--port` option

### Logging

The server provides detailed logging. Set the log level by modifying the `logging.basicConfig()` call in `server.py`.

### Debug Mode

For development, you can enable debug logging:
```python
logging.basicConfig(level=logging.DEBUG)
```

## License

[Add your license information here]

## Support

[Add support/contact information here] 