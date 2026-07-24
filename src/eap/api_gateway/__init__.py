"""API Gateway (Layer 6) - composition root, HTTP surface and CLI.

The only layer permitted to depend on every other layer.
"""

from eap.api_gateway.assembly import EapApplication, build_app, build_app_with_examples

__all__ = ["EapApplication", "build_app", "build_app_with_examples"]
