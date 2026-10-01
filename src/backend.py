from local_model import CONFIG_PATH
import tomllib

SDK_BACKEND = "sdk"
ARBITER_BACKEND = "arbiter"
_backend = SDK_BACKEND
_skip_images = False


# ##################################################################
# configure backend
# command-line choices stay in memory and never leak through process environment

def configure_backend(backend: str = SDK_BACKEND, skip_images: bool = False) -> None:
    global _backend, _skip_images
    if backend not in {SDK_BACKEND, ARBITER_BACKEND}:
        raise ValueError(f"Unsupported image backend: {backend}")
    _backend = backend
    _skip_images = skip_images


# ##################################################################
# get backend
# identify the current image route independently of the configured text model

def get_backend() -> str:
    return _backend


# ##################################################################
# use arbiter backend
# avoid routing still images through an unsupported GPU still-image backend

def use_arbiter_backend() -> bool:
    return _backend == ARBITER_BACKEND


# ##################################################################
# skip images
# honor a command-line switch or machine-local non-secret configuration

def skip_images() -> bool:
    if not CONFIG_PATH.exists():
        return _skip_images or use_arbiter_backend()
    config = tomllib.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    return _skip_images or use_arbiter_backend() or bool(config.get("skip_images", False))
