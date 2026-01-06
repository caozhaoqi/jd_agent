# JD Agent Docker Deployment Configuration

## Quick Start

```bash
# Build and start all services
docker-compose up -d --build

# View logs
docker-compose logs -f

# Stop all services
docker-compose down
```

## Services

### Redis Cache
- Port: 6379
- Health check enabled

### Backend API
- Port: 8000
- Auto-reload enabled in development
- Depends on Redis

### Frontend UI
- Port: 3001
- Next.js production mode
- Depends on Backend

## Environment Variables

### Backend
- `REDIS_URL`: Redis connection string (default: redis://redis:6379/0)
- `HF_ENDPOINT`: HuggingFace mirror URL

### Frontend
- `NEXT_PUBLIC_API_URL`: Backend API URL

## Development

For development with hot reload:

```bash
# Use development docker-compose override
docker-compose -f docker-compose.yml -f docker-compose.dev.yml up -d
```

## Production

Build optimized images:

```bash
docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build
```
