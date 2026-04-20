---
description: How to run tests for the project
---

# Run Tests

1. Ensure the development environment is running.
   ```bash
   make upd
   ```

2. Run the tests using the Makefile command.
   // turbo
   ```bash
   make tests
   ```

3. (Optional) If you need to run specific tests, use the docker command directly.
   ```bash
   docker-compose -f docker-compose.dev.yaml exec web python manage.py test apps/users/tests/test_api.py
   ```
