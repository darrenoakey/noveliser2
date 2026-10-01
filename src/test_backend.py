from backend import configure_backend, get_backend, skip_images, use_arbiter_backend
from generate_images import validate_image_backend
import pytest


def test_backend_choice_controls_real_image_route() -> None:
    configure_backend("sdk", False)
    assert get_backend() == "sdk"
    assert not use_arbiter_backend()
    validate_image_backend(get_backend())
    configure_backend("arbiter", False)
    assert use_arbiter_backend()
    assert skip_images()
    with pytest.raises(ValueError):
        validate_image_backend(get_backend())
    configure_backend("sdk", False)


def test_explicit_skip_images_does_not_change_backend() -> None:
    configure_backend("sdk", True)
    assert skip_images()
    assert get_backend() == "sdk"
    configure_backend("sdk", False)
