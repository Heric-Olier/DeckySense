"""Haptic services.

Business logic that composes ``HapticParams`` and applies them via a
``HapticBackend``. This layer knows about gain and curves; it does not
know whether the backend is InputPlumber, sysfs, or hidraw.
"""
