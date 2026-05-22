"""Model Registry: logical model name -> backend + weights + system prompt + retrieval profile.

The registry is the single seam between agent code and the inference backend.
Production migration from a persona prompt to a real LoRA fine-tune is a
registry update, not a code change.
"""

from axon.model_registry.client import ModelClient, get_client
from axon.model_registry.registry import REGISTRY, ModelSpec

__all__ = ["REGISTRY", "ModelClient", "ModelSpec", "get_client"]
