# Running PermitGate Gateway with Docker Compose

This document explains how to run the PermitGate Gateway API and PostgreSQL database using Docker Compose.

## Prerequisites

- Docker and Docker Compose installed on your system
- For Linux: Docker daemon running and user added to docker group

## Quick Start

### 1. Clone or navigate to the project

```bash
cd /path/to/permitgate/gateway
```

### 2. Configure environment variables (optional)

Copy `.env.example` to `.env` and customize as needed:

```bash
cp .env.example .env
```

Default values are provided for all environment variables, so this step is optional for local development.

### 3. Start the services

```bash
docker-compose up
```

This will:
- Build the gateway Docker image
- Start PostgreSQL on port 5432
- Run database migrations automatically
- Start the gateway API on port 8080

The gateway will be available at `http://localhost:8080`

Access the API documentation at:
- Swagger UI: http://localhost:8080/docs
- ReDoc: http://localhost:8080/redoc
- OpenAPI schema: http://localhost:8080/openapi.json

### 4. Stop the services

```bash
docker-compose down
```

To also remove the database volume:

```bash
docker-compose down -v
```

## Environment Variables

### Database Configuration

- `DB_HOST`: PostgreSQL hostname (default: `postgres`)
- `DB_PORT`: PostgreSQL port (default: `5432`)
- `DB_USER`: PostgreSQL username (default: `postgres`)
- `DB_PASSWORD`: PostgreSQL password (default: `postgres`)
- `DB_NAME`: Database name (default: `gateway`)
- `DB_RUN_MIGRATIONS`: Run Alembic migrations on startup (default: `true`)
- `DB_CREATE_DUMMY_DATA`: Create dummy/sample data (default: `true`)

### Gateway Configuration

- `GATEWAY_HOST`: Bind address (default: `0.0.0.0`)
- `GATEWAY_PORT`: Listen port (default: `8080`)

## Common Tasks

### View logs

```bash
# All services
docker-compose logs

# Specific service
docker-compose logs gateway
docker-compose logs postgres

# Follow logs
docker-compose logs -f
```

### Connect to PostgreSQL directly

```bash
docker-compose exec postgres psql -U postgres -d gateway
```

### Rebuild the gateway image

```bash
docker-compose up --build
```

### Run in background

```bash
docker-compose up -d
```

## Development Workflow

When making changes to the gateway code:

1. Edit files in `server/src/`
2. Rebuild the image: `docker-compose up --build`
3. Container will restart with new code

For faster iteration during development, consider running the gateway directly on your host machine instead:

```bash
# In the server directory
cd server
uv run main.py
```

This requires only PostgreSQL to run in Docker:

```bash
docker-compose up postgres
```

## Troubleshooting

### Gateway can't connect to PostgreSQL

Ensure PostgreSQL is healthy before the gateway starts. The docker-compose file uses `depends_on` with a health check to ensure this, but if issues persist:

```bash
# Check PostgreSQL health
docker-compose ps
docker-compose logs postgres
```

### Port already in use

Change the port in the docker-compose file or environment variables:

```bash
GATEWAY_PORT=8081 docker-compose up
DB_PORT=5433 docker-compose up
```

### Need to reset the database

```bash
docker-compose down -v
docker-compose up
```

This removes the database volume and creates a fresh database with migrations.

### Permission denied errors

On Linux, add your user to the docker group:

```bash
sudo usermod -aG docker $USER
newgrp docker
```

## Production Considerations

This docker-compose setup is optimized for local development. For production:

1. Use strong passwords for `DB_PASSWORD`
2. Set `DB_CREATE_DUMMY_DATA=false`
3. Use a separate database backup strategy
4. Configure proper networking and security groups
5. Use environment files or secrets management for sensitive data
6. Consider using managed database services instead of containerized PostgreSQL
7. Set up proper logging and monitoring
