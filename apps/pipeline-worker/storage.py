"""
Storage abstraction that selects Dropbox or Local FS at runtime.

Usage in pipeline code: `import storage` and call functions exported here.
"""
import os
import importlib

# Lazy-import backends to avoid import side effects

_BACKEND = os.getenv("STORAGE_BACKEND", "dropbox").lower()


def _backend_module():
    # Import modules without package-relative syntax so this works when
    # running from the directory (no package parent).
    module_name = "local_io" if _BACKEND == "local" else "dropbox_io"
    return importlib.import_module(module_name)


def ensure_folder(path: str):
    return _backend_module().ensure_folder(path)


def write_json(path: str, obj: dict):
    return _backend_module().write_json(path, obj)


def read_json(path: str) -> dict:
    return _backend_module().read_json(path)


def upload_pil_image(path: str, img, format: str = "JPEG"):
    return _backend_module().upload_pil_image(path, img, format)


def download_pil_image(path: str):
    return _backend_module().download_pil_image(path)


def list_folder(path: str):
    return _backend_module().list_folder(path)


def get_root() -> str:
    # Dropbox backend defines DROPBOX_ROOT via env; Local uses LOCAL_ROOT
    if _BACKEND == "local":
        mod = importlib.import_module("local_io")
        return mod.get_root()
    else:
        # Mirror existing behavior
        import os as _os
        root = _os.getenv("DROPBOX_ROOT", "/Apps/CreativeAutomation")
        # Normalize to single leading slash, no trailing slash (except root)
        root = "/" + root.lstrip("/")
        if len(root) > 1 and root.endswith("/"):
            root = root[:-1]
        return root


def upload_bytes(path: str, data: bytes):
    return _backend_module().upload_bytes(path, data)


def download_bytes(path: str) -> bytes:
    return _backend_module().download_bytes(path)


def delete_path(path: str):
    return _backend_module().delete_path(path)
