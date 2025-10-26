#!/usr/bin/env python3
"""
Temporary shim: expose EnhancedLogger separate from msm monolith.
Will be replaced by extracted core/logger.py
"""
from msm import EnhancedLogger as _Logger

class EnhancedLogger(_Logger):
    pass
