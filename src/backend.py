import os


SDK_BACKEND = "sdk"
ARBITER_BACKEND = "arbiter"
BACKEND_ENV = "NOVELISER2_BACKEND"
ARBITER_BASE_URL_ENV = "NOVELISER2_ARBITER_BASE_URL"
ARBITER_HIGH_MODEL_ENV = "NOVELISER2_ARBITER_HIGH_MODEL"
ARBITER_LOW_MODEL_ENV = "NOVELISER2_ARBITER_LOW_MODEL"
SKIP_IMAGES_ENV = "NOVELISER2_SKIP_IMAGES"


def get_backend() -> str:
    backend = os.environ.get(BACKEND_ENV, SDK_BACKEND).strip().lower()
    if backend not in {SDK_BACKEND, ARBITER_BACKEND}:
        raise ValueError(f"Unsupported backend: {backend}")
    return backend


def use_arbiter_backend() -> bool:
    return get_backend() == ARBITER_BACKEND


def get_arbiter_base_url() -> str:
    return os.environ.get(ARBITER_BASE_URL_ENV, "http://10.0.0.254:8400").rstrip("/")


def get_arbiter_text_model(model: str) -> str:
    if model == "haiku":
        return os.environ.get(ARBITER_LOW_MODEL_ENV, os.environ.get(ARBITER_HIGH_MODEL_ENV, "gemma4-26b"))
    return os.environ.get(ARBITER_HIGH_MODEL_ENV, "gemma4-26b")


def skip_images() -> bool:
    value = os.environ.get(SKIP_IMAGES_ENV, "").strip().lower()
    return value in {"1", "true", "yes", "on"}
