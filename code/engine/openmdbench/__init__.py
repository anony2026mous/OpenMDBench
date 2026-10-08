"""Public package entry point for OpenMDBench."""

from importlib.metadata import PackageNotFoundError, version

from gymnasium.envs.registration import register

try:
    __version__ = version("openmdbench")
except PackageNotFoundError:  # pragma: no cover - source tree without installation
    __version__ = "0.1.0"

register(
    id="OpenMDBench-SurfaceSmoke-v0",
    entry_point="openmdbench.envs:SurfaceSmokeEnv",
)
register(
    id="OpenMDBench-v1",
    entry_point="openmdbench.envs:OpenMDBenchEnv",
)

__all__ = ["__version__"]
