from dynamic_overload import overload
from typing import Iterable
from dynamic_overload.overload import NoMatchingOverloadException
import pytest


@overload
def flatten(x: int) -> Iterable[int]:
    """Flatten an integer."""
    yield x


@overload
def flatten(x: Iterable[int]) -> Iterable[int]:
    """Flatten an iterable of integers."""
    return (y for z in x for y in flatten(z))


def test_flatten():
    assert list(flatten(1)) == [1]
    assert list(flatten([1, 2, 3])) == [1, 2, 3]
    assert list(flatten([[1, 2], [3, 4]])) == [1, 2, 3, 4]
    assert list(flatten([1, [2, 3], [4, [5, 6]]])) == [1, 2, 3, 4, 5, 6]
    assert list(flatten([1, [2, 3], [4, [5, 6]]])) == [1, 2, 3, 4, 5, 6]


def test_flatten_invalid():
    with pytest.raises(NoMatchingOverloadException):
        flatten(1.0)

    with pytest.raises(NoMatchingOverloadException):
        flatten(None)


def test_help():
    msg = (
        "Overloaded function 'flatten' with 2 signatures:\n"
        "- (x: int) -> Iterable[int]: Flatten an integer.\n"
        "- (x: Iterable[int]) -> Iterable[int]: Flatten an iterable of integers."
    )
    assert flatten.__doc__ == msg
    assert flatten.__name__ == "flatten"
    assert flatten.__module__ == "test_functions"
    assert flatten.__qualname__ == "flatten"

    assert flatten.help(1) == "Flatten an integer."
    assert flatten.help([1, 2, 3]) == "Flatten an iterable of integers."

    with pytest.raises(NoMatchingOverloadException):
        flatten.help(1.0)
