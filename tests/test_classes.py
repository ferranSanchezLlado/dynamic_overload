from dynamic_overload import OverloadMeta, Overload
from dynamic_overload.overload import ConflictingOverloadWarning, NoMatchingOverloadException
import pytest


class Test(metaclass=OverloadMeta):
    __test__ = False  # disables pytest collection
    x: int | str | float | None
    y: float | None
    args: tuple[int, ...]
    kwargs: dict[str, int]
    _which: int

    def __init__(self, x: int):
        self.x = x
        self.y = None
        self.args = ()
        self.kwargs = {}
        self._which = 1

    def __init__(self, x: str):
        self.x = x
        self.y = None
        self.args = ()
        self.kwargs = {}
        self._which = 2

    def __init__(self, x: int, y: float):
        self.x = x
        self.y = y
        self.args = ()
        self.kwargs = {}
        self._which = 3

    def __init__(self, x: str, y: float, *args: int, **kwargs: int):
        self.x = x
        self.y = y
        self.args = args
        self.kwargs = kwargs
        self._which = 4

    def __init__(self, x: float | None = None):
        self.x = x
        self.y = None
        self.args = ()
        self.kwargs = {}
        self._which = 5


def test_init_1():
    t1 = Test(1)
    assert t1.x == 1
    assert t1.y is None
    assert t1.args == ()
    assert t1.kwargs == {}
    assert t1._which == 1


def test_init_2():
    t2 = Test("1")
    assert t2.x == "1"
    assert t2.y is None
    assert t2.args == ()
    assert t2.kwargs == {}
    assert t2._which == 2


def test_init_3():
    t3 = Test(1, 2.0)
    assert t3.x == 1
    assert t3.y == 2.0
    assert t3.args == ()
    assert t3.kwargs == {}
    assert t3._which == 3


def test_init_4():
    t4 = Test("1", 2.0, 3, 4, 5, a=1, b=2, c=3)
    assert t4.x == "1"
    assert t4.y == 2.0
    assert t4.args == (3, 4, 5)
    assert t4.kwargs == {"a": 1, "b": 2, "c": 3}
    assert t4._which == 4


def test_init_5():
    t5 = Test()
    assert t5.x is None
    assert t5.y is None
    assert t5.args == ()
    assert t5.kwargs == {}
    assert t5._which == 5

    t5_2 = Test(1.0)
    assert t5_2.x == 1.0
    assert t5_2.y is None
    assert t5_2.args == ()
    assert t5_2.kwargs == {}
    assert t5_2._which == 5


def test_init_invalid_1():
    with pytest.raises(NoMatchingOverloadException):
        Test([])


def test_init_invalid_2():
    with pytest.raises(NoMatchingOverloadException):
        Test(1.0, 2)


def test_init_invalid_3():
    with pytest.raises(NoMatchingOverloadException):
        Test(1, 2, 3, 4, 5, 6, 7, 8, 9, 10)


def test_init_invalid_4():
    with pytest.raises(NoMatchingOverloadException):
        Test(1, 2, 3, 4, 5, a=1, b=2, c=3)


def test_init_invalid_5():
    with pytest.raises(NoMatchingOverloadException):
        Test(None, None, None, None, None, a=1, b=2, c=3)


def test_similar_signature_1():
    with pytest.warns(ConflictingOverloadWarning):

        class SaysHey(Overload):
            def hello(self, x: int):
                pass

            def hello(self, x: int, y: int | None = None):
                pass


def test_similar_signature_2():
    with pytest.warns(ConflictingOverloadWarning):

        class SaysHey(Overload):
            def hello(self, x):
                pass

            def hello(self, x: int):
                pass


def test_similar_signature_3():
    with pytest.warns(ConflictingOverloadWarning):

        class SaysHey(Overload):
            def hello(self, x: int = 1):
                pass

            def hello(self, x: int = 2, y: int = 3):
                pass


def test_similar_signature_4():
    with pytest.warns(ConflictingOverloadWarning):

        class SaysHey(Overload):
            def hello(self, x: int = 1):
                pass

            def hello(self, x: int = 2):
                pass


def test_similar_signature_5():
    with pytest.warns(ConflictingOverloadWarning):

        class SaysHey(Overload):
            def hello(self, x: int):
                pass

            def hello(self, x: float):
                pass

            def hello(self, x: str):
                pass

            def hello(self, x: int | float | str):
                pass
