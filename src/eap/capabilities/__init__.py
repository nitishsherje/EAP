"""Capabilities (Layer 4) - Capability Manager and ToolClients."""

from eap.capabilities.base import CapabilityResult, ToolClient
from eap.capabilities.manager import CapabilityManager
from eap.capabilities.native import NativeToolRegistry

__all__ = [
    "CapabilityManager",
    "CapabilityResult",
    "NativeToolRegistry",
    "ToolClient",
]
