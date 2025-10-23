# Kubernetes Deployment

This directory contains Kubernetes manifests for deploying the Hill Hill backend Flask app.

## Files

- **`deployment.yaml`** - Deployment and Service configuration (ClusterIP)
- **`ingress.yaml`** - Ingress configuration using shared ALB
- **`secrets.yaml`** - Secret configuration for JWT key (template)

## Prerequisites

1. Kubernetes cluster configured (EKS)
2. `kubectl` installed and configured
3. Docker image pushed to ECR: `714364484263.dkr.ecr.us-east-1.amazonaws.com/hill-hill-game-dev:latest`
4. AWS Load Balancer Controller installed on the cluster
5. Shared ALB deployed (`~/src/personal-terraform/k8s/shared-alb.yaml`)

## Setup

### 1. Create/Update Secret

**Important:** Generate a secure JWT secret key before deploying!

```bash
# Generate a secure random key
python3 -c "import secrets; print(secrets.token_hex(32))"

# Edit secrets.yaml and replace the jwt-secret-key value
vim k8s/secrets.yaml
```

### 2. Apply Secrets

```bash
kubectl apply -f k8s/secrets.yaml
```

### 3. Deploy the Application

```bash
# Deploy the application and service
kubectl apply -f k8s/deployment.yaml

# Deploy the ingress (uses shared ALB)
kubectl apply -f k8s/ingress.yaml
```

### 4. Verify Deployment

```bash
# Check pods
kubectl get pods -l app=hill-hill-backend

# Check service
kubectl get service hill-hill-backend-service

# Check ingress (should show shared ALB address)
kubectl get ingress hill-hill-backend-ingress

# Check logs
kubectl logs -l app=hill-hill-backend --tail=50 -f
```

## Access the Service

### Get the Shared ALB Hostname

```bash
# Get the ALB hostname from the shared ALB ingress
kubectl get ingress shared-alb -o jsonpath='{.status.loadBalancer.ingress[0].hostname}'

# Or from your backend ingress
kubectl get ingress hill-hill-backend-ingress
```

The backend will be accessible via the shared ALB at these paths:
- `http://<ALB-HOSTNAME>/app`
- `http://<ALB-HOSTNAME>/validate`
- `http://<ALB-HOSTNAME>/api/*`
- `http://<ALB-HOSTNAME>/test`

### Test the API

```bash
# Get ALB hostname
ALB_HOST=$(kubectl get ingress shared-alb -o jsonpath='{.status.loadBalancer.ingress[0].hostname}')

# Test the endpoints
curl http://${ALB_HOST}/app
curl http://${ALB_HOST}/test
curl -X POST http://${ALB_HOST}/validate -H "Content-Type: application/json" -d '{"session":"test"}'
```

## Update Deployment

### After pushing a new image

```bash
# Option 1: Update image and rollout
kubectl set image deployment/hill-hill-backend flask-app=714364484263.dkr.ecr.us-east-1.amazonaws.com/hill-hill-game-dev:v1.0.0

# Option 2: Restart deployment (if using :latest tag)
kubectl rollout restart deployment/hill-hill-backend

# Check rollout status
kubectl rollout status deployment/hill-hill-backend
```

## Scaling

```bash
# Scale to 3 replicas
kubectl scale deployment/hill-hill-backend --replicas=3

# Verify
kubectl get pods -l app=hill-hill-backend
```

## Debugging

```bash
# Get pod details
kubectl describe pod -l app=hill-hill-backend

# Get logs from specific pod
kubectl logs <pod-name>

# Get logs from all pods
kubectl logs -l app=hill-hill-backend --all-containers=true

# Execute command in pod
kubectl exec -it <pod-name> -- /bin/bash

# Port forward for local testing (bypass LoadBalancer)
kubectl port-forward service/hill-hill-backend-service 8080:80
# Then access at http://localhost:8080/app
```

## Cleanup

```bash
# Delete deployment and service
kubectl delete -f k8s/deployment.yaml

# Delete secrets
kubectl delete -f k8s/secrets.yaml
```

## Configuration

### Environment Variables

Configured in `deployment.yaml`:
- `FLASK_ENV`: Set to "production"
- `JWT_SECRET_KEY`: Loaded from Kubernetes secret

### Resources

Current limits per pod:
- Memory: 128Mi (request) / 512Mi (limit)
- CPU: 100m (request) / 500m (limit)

Adjust in `deployment.yaml` based on your needs.

### Health Checks

- **Liveness Probe**: Checks if the app is alive (restarts if failing)
- **Readiness Probe**: Checks if the app is ready to accept traffic

Both probe the `/app` endpoint.

## Shared ALB Architecture

This deployment uses a **shared Application Load Balancer** configured in `~/src/personal-terraform/k8s/shared-alb.yaml`.

### Benefits:
- ✅ **Cost Savings**: One ALB shared by multiple services
- ✅ **Centralized Management**: Single ALB configuration
- ✅ **Path-based Routing**: Each service gets its own paths

### How It Works:
The annotation `alb.ingress.kubernetes.io/group.name: shared-web-alb` tells the AWS Load Balancer Controller to use the existing shared ALB instead of creating a new one.

### Adding More Services:
When you add new services, just create their ingress with:
```yaml
annotations:
  alb.ingress.kubernetes.io/group.name: shared-web-alb
  alb.ingress.kubernetes.io/group.order: '20'  # Higher number for priority
```

## Production Considerations

- [ ] Generate and set a secure `JWT_SECRET_KEY` in secrets.yaml
- [ ] Consider using AWS Secrets Manager or HashiCorp Vault instead of Kubernetes secrets
- [ ] Set up Horizontal Pod Autoscaler (HPA) for auto-scaling
- [ ] Configure resource limits based on load testing
- [ ] Add SSL/TLS certificate to the shared ALB
- [ ] Set up monitoring and alerting
- [ ] Configure log aggregation (CloudWatch, ELK, etc.)
- [ ] Use specific image tags instead of `:latest` for production
- [ ] Configure proper health check paths for each service


