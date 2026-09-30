from importlib.util import cache_from_source
from pathlib import Path

from app.constants import update_installation as settings
from app.updates.install_state import safe_path, sync_directory


def purge_source_bytecode(root, name):
    source = Path(root) / name
    if source.suffix != settings.PYTHON_SOURCE_SUFFIX:
        return
    for optimization in settings.PYTHON_CACHE_OPTIMIZATIONS:
        cache = Path(cache_from_source(str(source), optimization=optimization))
        destination = safe_path(root, cache.relative_to(root))
        if destination.exists() and not destination.is_file():
            raise ValueError("Bytecode cache is not a regular file")
        destination.unlink(missing_ok=True)
        if destination.parent.exists():
            sync_directory(destination.parent)
