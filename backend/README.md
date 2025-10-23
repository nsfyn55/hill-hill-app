# Backend Flask App

JWT authentication service for the Hill Hill App.

## Local Development

### Start with Podman (with volume mapping)
```bash
cd backend
./run-dev.sh
```

The app will be available at `http://localhost:5001/app`

Source changes in `./src` will be reflected immediately without rebuilding.

### Stop
Press `Ctrl+C` to stop the container.

### Alternative: Using docker-compose.yml
If you have `podman-compose` installed:
```bash
podman-compose up
```

## API Endpoints

### GET /app
Returns a JWT token with session and role claim.

**Response:**
```json
{
  "token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
  "session": "a1b2c3d4...",
  "role": "User"
}
```

## Deployment to ECR

### Prerequisites
- Podman installed
- AWS CLI configured with appropriate credentials

### Deploy
```bash
cd backend
./push-to-dev.sh [tag]  # tag is optional, defaults to 'latest'
```

### Example
```bash
./push-to-dev.sh v1.0.0
```

## Testing
```bash
curl http://localhost:5001/app
```

