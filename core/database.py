#!/usr/bin/env python3
"""
Temporary shim: expose DatabaseManager separate from msm monolith.
Will be replaced by extracted core/database.py
"""
from msm import DatabaseManager as _DB

class DatabaseManager(_DB):
    pass
