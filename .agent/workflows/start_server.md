---
description: How to start the development server
---

# Start Server

1. Build the containers (if new dependencies were added).
   ```bash
   make build
   ```

2. Start the services in detached mode.
   // turbo
   ```bash
   make upd
   ```

3. View logs (optional).
   ```bash
   docker-compose -f docker-compose.dev.yaml logs -f
   ```
