"""Kubernetes backend for jupyter-scheduler."""

# Import k8s_orm FIRST to auto-install K8s database backend before anything else
from . import k8s_orm

from .executors import K8sExecutionManager

__version__ = "0.1.0"
__all__ = ["K8sExecutionManager"]
