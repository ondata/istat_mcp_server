# istat-mcp-server Helm chart

Deploys the ISTAT MCP server on Kubernetes as a stateless HTTP service.

The server speaks MCP over stdio by default. This chart runs the **HTTP host**
(`istat_mcp_server.http_server`, console script `istat-mcp-http`): a small Starlette/uvicorn
application that mounts `create_server()` as a stateless streamable-HTTP MCP app at `/mcp`
and exposes `/health` for probes. All data comes from the public ISTAT
SDMX API, so the deployment needs no database, no persistent volume and no cloud identity.

## What gets installed

| Resource | Default | Notes |
|---|---|---|
| Deployment | always | non-root, read-only root filesystem, `/tmp` emptyDir for logs and cache |
| Service | `ClusterIP:8000` | `PORT` in the container follows `service.port` |
| HorizontalPodAutoscaler | enabled | CPU target 80 %, 1 replica (ISTAT rate-limits by IP, see `values.yaml`) |
| PodDisruptionBudget | enabled | `minAvailable: 1` |
| NetworkPolicy | enabled | ingress from the chart namespace only, or from `ingressNamespaces` / Gateway namespace / `ingressCIDRs`; egress DNS + TCP 443 |
| Gateway API `HTTPRoute` (+ optional `Gateway`, HTTP→HTTPS redirect) | disabled | `gateway.enabled` |
| `GCPBackendPolicy`, `HealthCheckPolicy` | disabled | GKE only |
| Secret or `SecretStore` + `ExternalSecret` | only with `auth.enabled` | bearer token for `/mcp` |

## Prerequisites

- Kubernetes >= 1.29, Helm >= 3.12.
- A container image of the HTTP host, pushed to a registry you control. No public image is
  published yet: build it with the `Dockerfile` at the repository root (it installs the
  package with the `http` extra from `uv.lock`) and set `image.repository` / `image.tag`.
- Optional: Gateway API CRDs and a `GatewayClass` (`gateway.enabled`), External Secrets
  Operator with a HashiCorp Vault backend (`externalSecrets.enabled`), Istio (`mesh.enabled`).

## Install

```bash
helm install istat ./charts/istat-mcp-server \
  --namespace istat-mcp --create-namespace \
  --set image.repository=registry.example.com/istat-mcp-server \
  --set image.tag=0.1.0
```

Smoke test from the cluster:

```bash
kubectl -n istat-mcp port-forward svc/istat-istat-mcp-server 8000:8000
curl http://localhost:8000/health          # {"status":"ok"}
# MCP streamable-HTTP endpoint (trailing slash required; /mcp redirects with 307).
# The host runs in stateless mode: every request is self-contained, so no initialize
# handshake is needed before tools/list.
curl -X POST http://localhost:8000/mcp/ -H 'Content-Type: application/json' \
  -H 'Accept: application/json, text/event-stream' \
  -d '{"jsonrpc":"2.0","id":1,"method":"tools/list"}'
```

## Exposure through Gateway API

Attach to an existing Gateway:

```yaml
gateway:
  enabled: true
  name: shared-gateway
  namespace: infra-gateway
httpRoute:
  hostnames: ["mcp.example.com"]
```

Create a dedicated Gateway (`gateway.create: true`): set `gateway.className`, the listeners
and either `tls.certificateRefs` on the HTTPS listener or a platform annotation on the
Gateway. The HTTP listener only serves the 301 redirect route (`httpsRedirect`).

## Authentication

`auth.enabled: true` injects `MCP_ISTAT_TOKEN` from a Secret and the HTTP host then requires
`Authorization: Bearer <token>` on `/mcp` (`/health` stays open). The Secret comes from:

- a plain `Secret` rendered from `externalSecrets.secrets.token.plaintext` when
  `externalSecrets.enabled: false` (pass the value with `--set` or an untracked values file;
  an empty value makes `helm template` fail and the server refuses to start with an empty token);
- an `ExternalSecret` synced from Vault when `externalSecrets.enabled: true`
  (`externalSecrets.vault.*` describes the Kubernetes-auth `SecretStore`).

## Environment variables

| Variable | Default | Purpose |
|---|---|---|
| `PORT` | `service.port` | HTTP listen port |
| `LOG_DIR` | `/tmp/istat-log` | upstream log directory (must be writable, one level under `/tmp`) |
| `PERSISTENT_CACHE_DIR` | `/tmp/istat-cache` | upstream disk cache |
| `ISTAT_DB_PATH` | unset | path of the bundled DuckDB file; enables `get_territorial_codes` |
| `MCP_ISTAT_TOKEN` | unset | bearer token, set by the chart when `auth.enabled` |

Add further variables under `env`.

## Values

See `values.yaml`; every key is documented inline. The most relevant ones:

| Key | Default | Description |
|---|---|---|
| `image.repository` / `image.tag` | `istat-mcp-server` / appVersion | HTTP host image |
| `namespace` | release namespace | target namespace |
| `service.type` / `service.port` | `ClusterIP` / `8000` | Service exposure |
| `autoscaling.*`, `podDisruptionBudget.*` | enabled | availability settings |
| `networkPolicy.ingressNamespaces` | `[]` | namespaces allowed to reach the pod; include the gateway proxy namespace if it differs from the Gateway's |
| `networkPolicy.ingressCIDRs` | `[]` | CIDRs allowed to reach the pod (e.g. cloud LB ranges for GKE Gateway) |
| `networkPolicy.egressPorts` | `[443]` | allowed egress TCP ports |
| `auth.enabled` | `false` | bearer auth on `/mcp` |
| `gateway.enabled` / `gateway.create` | `false` / `false` | Gateway API exposure |
| `httpRoute.hostnames` | `[]` | hostnames on the HTTPRoute |
| `backendPolicy.enabled` / `healthCheckPolicy.enabled` | `false` | GKE policies |
| `externalSecrets.enabled` | `false` | Vault-backed Secret via External Secrets Operator |
| `mesh.enabled` / `mesh.mode` | `false` / `ambient` | Istio enrollment labels |
| `env` | log/cache dirs | environment passed to the server |
