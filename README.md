# FleetMind AI

FleetMind AI is an advanced Agentic AI orchestration platform for a simulated autonomous last-mile delivery fleet.

FleetMind does not implement autonomous driving, SLAM, steering, LiDAR processing, or low-level vehicle control.

Instead, it is the intelligent operational layer responsible for mission planning, event handling, tool selection, routing between specialist agents, policy enforcement, recovery, evaluation, and human approval.

## Current Status

### Phase 1 — Foundations & Digital Twin

Implemented:

- FastAPI backend foundation
- Pydantic configuration and domain models
- PostgreSQL infrastructure
- Redis infrastructure
- Redis Stream event foundation
- NetworkX city graph
- simulated delivery van
- battery simulation
- packages and delivery stops
- deterministic multi-stop missions
- package verification
- mission events
- structured logging
- Docker Compose environment
- automated tests

Agentic AI components are intentionally introduced in later phases after the simulation environment is validated.

## Core Boundary

FleetMind assumes a lower-level autonomous vehicle platform already exposes safe capabilities such as:

- navigate_to
- stop_vehicle
- get_vehicle_state
- get_location
- get_battery
- open_delivery_compartment
- verify_package
- capture_image
- return_to_hub

FleetMind decides when and why these capabilities should be used.

## Phase 1 Architecture

HTTP / CLI
→ FastAPI
→ Deterministic Mission Runner
→ Digital Twin
→ NetworkX City
→ State Changes
→ Fleet Events
→ Redis Streams

PostgreSQL and Redis provide the initial persistent infrastructure foundation.

## Local Development

Start infrastructure:

```bash
docker compose up -d postgres redis
```
