# Dynamic Overload

Dynamic Overload is a python package that allows you to overload functions and classes using dynamic dispatch depending on the type of the arguments. This allows you to write more readable code and avoid using isinstance and type checks.

The package also detects collisions between the overloads and warns the user about them without breaking the code. In case of collision, the first overload is used. So, its recomended that you put the most specific overloads first before the more general ones.

## Installation

Requires python 3.10 or higher

```bash
pip install dynamic-overload
```

## Usage

For functions:
```python
from dynamic_overload import overload
from typing import Iterable

@overload
def flatten(x: Iterable[int]) -> Iterable[int]:
    return [y for l in x for y in flatten(l)]

@overload
def flatten(x: int) -> Iterable[int]:
    yield x

assert list(flatten([1, [2, 3], 4])) == [1, 2, 3, 4]
assert list(flatten(1)) == [1]
```

For classes:
```python
from dynamic_overload import OverloadMeta

class Integer(metaclass=OverloadMeta):
    x: int

    def __init__(self, x: int):
        self.x = x

    def __init__(self, x: str):
        self.x = int(x)

    def __init__(self, x: float):
        self.x = int(x)

assert Integer(1).x == 1
assert Integer('1').x == 1
assert Integer(1.0).x == 1
```

The package also supports inheritance similar to python [abc](https://docs.python.org/3/library/abc.html) module. So the previous example can be rewritten as:
```python
from dynamic_overload import Overload

class Integer(Overload):
    x: int

    def __init__(self, x: int):
        self.x = x

    def __init__(self, x: str):
        self.x = int(x)

    def __init__(self, x: float):
        self.x = int(x)

assert Integer(1).x == 1
assert Integer('1').x == 1
assert Integer(1.0).x == 1
```

## License

[MIT](https://choosealicense.com/licenses/mit/)
```

