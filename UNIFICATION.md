# MSM Unified Merge Plan

This branch will unify `main` and `main-v1.1.0` into a single modular codebase with enterprise features.

Steps:
1. Keep `main` as base (Termux-native, SQLite, monitoring, logging).
2. Gradually modularize `msm.py` into packages: core/, managers/, flavors/, ui/, utils/.
3. Port v1.1.0 modules (api_client.py, server_manager.py, world_manager.py, tunnel_manager.py, environment.py, ui.py) into managers/ and core/ while integrating DB/logging/monitoring.
4. Bring back tunneling integrations from v1.1.0.
5. Preserve tests from v1.1.0 and add tests for DB/monitoring.

Tracking checklist:
- [ ] Create package skeleton
- [ ] Extract core: database.py, logger.py, monitoring.py
- [ ] Move config handling to core/config.py
- [ ] Move UI into ui/
- [ ] Port v1.1.0 managers (server/world/tunnel)
- [ ] Extract flavor logic into flavors/
- [ ] Replace direct calls in msm.py with imports
- [ ] Restore tunneling (playit, ngrok, cloudflared, pinggy)
- [ ] Add tests/ from v1.1.0
- [ ] Update README for unified structure
