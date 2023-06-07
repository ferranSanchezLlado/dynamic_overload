""" This module provides the core functionality for dynamic_overload. """
# https://peps.python.org/pep-3124/
from typing import Any, Callable, TypeVar, Generic, Dict, Type, Tuple, List, Union
from types import UnionType  # type: ignore
from inspect import signature, Signature, Parameter, BoundArguments
import warnings


# message, category, filename, lineno, line=None
warnings.formatwarning = (
    lambda message, category, filename, lineno, _line=None: f"{filename}:{lineno}: {category.__name__}: {message}\n"
)


class NoMatchingOverloadException(Exception):
    """Raised when no matching overload function is found."""


class ConflictingOverloadWarning(Warning):
    """Raised when two or more overload functions have the similar signatures that could result in a collision.
    Default behavior is to ignore the warning and use the first overload function that matches the arguments."""


class OverloadDict(Dict[str, Any]):
    """A dictionary that allows overloading of methods. Other than that, it behaves like a normal dictionary."""

    def __setitem__(self, key: str, value: Any) -> None:
        if not callable(value):
            super().__setitem__(key, value)
            return

        current_value = self.get(key, None)
        if current_value is None:
            super().__setitem__(key, OverloadItem(value))
        elif isinstance(current_value, OverloadItem):
            current_value.append(value)
        else:
            raise TypeError(f"Overloaded method {key} must be a function")


def _score_type_hint(arg: Any, hint: Type) -> int:
    """Returns a score based on how well the argument matches the type hint.

    Returns -1 if the argument does not match the type hint.
    Returns 0 if the type hint is Any or not specified.
    Returns 1 if the argument matches the type hint (including Union types).
    """
    # Remove parameterized types (e.g. List[int] -> List)
    if hasattr(hint, "__origin__"):
        hint = hint.__origin__

    if hint is Parameter.empty or hint is Any:
        return 0

    if isinstance(hint, UnionType):
        for subhint in hint.__args__:
            if _score_type_hint(arg, subhint) > 0:
                return 1
        return -1

    if isinstance(arg, hint):
        return 1
    return -1  # no match


def _score_any_type_hint(arg: Any, param: Parameter) -> int:
    """Returns a score based on how well the argument matches the type hint.
    This function can handle *args and **kwargs.

    Returns -1 if the argument does not match the type hint.
    Returns 0 if the type hint is Any or not specified.
    Returns 1 if the argument matches the type hint (including Union types).
    """
    hint = param.annotation
    # Check if its *args
    if param.kind is Parameter.VAR_POSITIONAL:
        return sum(_score_type_hint(a, hint) for a in arg)
    # Check if its **kwargs
    if param.kind is Parameter.VAR_KEYWORD:
        return sum(_score_type_hint(a, hint) for a in arg.values())
    # Otherwise, its a single argument
    return _score_type_hint(arg, hint)


def _signature_matches(sig: Signature, bound_args: BoundArguments) -> int:
    """Returns a score based on how well the arguments match the signature.

    Returns -1 if the arguments do not match the signature.
    Returns a positive integer if the arguments match the signature.
    """
    score = 0
    for name, arg in bound_args.arguments.items():
        partial_score = _score_any_type_hint(arg, sig.parameters[name])
        if partial_score < 0:
            return -1
        score += partial_score
    return score


def _overlap_signature(sig1: Signature, sig2: Signature) -> bool:
    """Returns True if the signatures overlap, False otherwise."""
    # Check for default values
    len_sig1_defaults = sum(1 for param in sig1.parameters.values() if param.default is not Parameter.empty)
    len_sig2_defaults = sum(1 for param in sig2.parameters.values() if param.default is not Parameter.empty)
    # Preventive check if default values could result in a collision (e.g. f(a) and f(a, b=1))
    if (
        len(sig1.parameters) != len(sig2.parameters)
        and len(sig1.parameters) != len(sig2.parameters) - len_sig2_defaults
        and len(sig1.parameters) - len_sig1_defaults != len(sig2.parameters)
        and len(sig1.parameters) - len_sig1_defaults != len(sig2.parameters) - len_sig2_defaults
    ):
        return False
    for name, param in sig1.parameters.items():
        if name not in sig2.parameters:
            continue
        other_param = sig2.parameters[name]
        # Remove parameterized types (e.g. List[int] -> List)
        if hasattr(param.annotation, "__origin__"):
            param = param.replace(annotation=param.annotation.__origin__)
        if hasattr(other_param.annotation, "__origin__"):
            other_param = other_param.replace(annotation=other_param.annotation.__origin__)

        # Handle non-annotated parameters and parameters with Any type
        if (
            param.annotation is Parameter.empty
            or other_param.annotation is Parameter.empty
            or param.annotation is Any
            or other_param.annotation is Any
        ):
            continue
        # Handle Union types and Optional types
        if isinstance(param.annotation, UnionType) or isinstance(other_param.annotation, UnionType):
            params1: tuple = (param.annotation,)
            params2: tuple = (other_param.annotation,)
            if isinstance(param.annotation, UnionType):
                params1 = param.annotation.__args__
            if isinstance(other_param.annotation, UnionType):
                params2 = other_param.annotation.__args__
            # Sort by length
            if len(params1) > len(params2):
                params1, params2 = params2, params1

            if not any(p in params2 for p in params1):
                return False
        # Handle non-Union types
        elif param.annotation != other_param.annotation:
            return False

    return True


T = TypeVar("T")


class BoundOverloadDispatcher(Generic[T]):
    """A class that dispatches overloaded methods based on the arguments. This dispatcher is bound to be used with a
    specific instance of a class.

    This class is not meant to be used directly. Instead, use the `OverloadMeta` metaclass to create overloaded methods.
    """

    # pylint: disable=too-many-arguments
    def __init__(
        self,
        instance: T,
        owner_cls: Type[T],
        name: str,
        overload_list: List[Callable],
        signatures: List[Signature],
    ) -> None:
        """Initializes the dispatcher."""
        self.instance = instance
        self.owner_cls = owner_cls
        self.name = name
        self.overload_list = overload_list
        self.signatures = signatures

    def best_match(self, *args: Any, **kwargs: Any) -> Callable:
        """Returns the best matching overload based on the arguments."""
        best_score, best_func = -1, None
        for func, sig in zip(self.overload_list, self.signatures):
            try:
                bound_args = sig.bind(self.instance, *args, **kwargs)
            except TypeError:  # missing/extra/unexpected args or kwargs
                continue
            bound_args.apply_defaults()
            score = _signature_matches(sig, bound_args)
            if score > best_score:
                best_score, best_func = score, func

        if best_func is None:
            raise NoMatchingOverloadException()
        return best_func

    def __call__(self, *args: Any, **kwargs: Any) -> Any:
        """Calls the best matching overload."""
        try:
            func = self.best_match(*args, **kwargs)
        except NoMatchingOverloadException:
            pass
        else:
            return func(self.instance, *args, **kwargs)

        # no matching overload in owner class, check next in line
        super_instance = super(self.owner_cls, self.instance)
        super_call = getattr(super_instance, self.name, None)
        if super_call is not None:
            try:
                return super_call(*args, **kwargs)
            except TypeError:
                pass
        raise NoMatchingOverloadException()


class FunctionOverloadDispatcher:
    """A class that dispatches overloaded functions based on the arguments. This dispatcher is intended to be used
    with functions that are not bound to a specific instance of a class.

    This class is not meant to be used directly. Instead, use the `overload` decorator.
    """

    def __init__(self, name: str, overload_list: List[Callable], signatures: List[Signature]) -> None:
        """Initializes the dispatcher."""
        self.name = name
        self.overload_list = overload_list
        self.signatures = signatures

    def best_match(self, *args: Any, **kwargs: Any) -> Callable:
        """Returns the best matching overload based on the arguments."""
        best_score, best_func = -1, None
        for func, sig in zip(self.overload_list, self.signatures):
            try:
                bound_args = sig.bind(*args, **kwargs)
            except TypeError:
                continue
            bound_args.apply_defaults()
            score = _signature_matches(sig, bound_args)
            if score > best_score:
                best_score, best_func = score, func

        if best_func is None:
            raise NoMatchingOverloadException()
        return best_func

    def __call__(self, *args: Any, **kwargs: Any) -> Any:
        """Calls the best matching overload."""
        func = self.best_match(*args, **kwargs)
        return func(*args, **kwargs)


class OverloadItem(Generic[T]):
    """A class that represents an overloaded method or function."""

    name: str
    overloads: List[Callable]
    signatures: List[Signature]

    def __init__(self, func: Callable) -> None:
        """Initializes the overload item."""
        self.name = func.__name__
        self.overloads = [func]
        self.signatures = [signature(func)]

        self.__name__ = func.__name__
        self.__qualname__ = func.__qualname__
        self.__module__ = func.__module__
        self.__annotations__ = func.__annotations__

    def append(self, func: Callable) -> None:
        """Appends a new overload to the item."""
        sig = signature(func)
        for existing_sig in self.signatures:
            if _overlap_signature(sig, existing_sig):
                warnings.warn(
                    f"Overload collision: {func.__name__}, {sig} with {existing_sig}. "
                    "In case of conflict on runtime, the first overload will be used.",
                    ConflictingOverloadWarning,
                )
        self.overloads.append(func)
        self.signatures.append(sig)

    def __get__(self, instance: T, owner_cls: Type[T]) -> BoundOverloadDispatcher[T]:
        """Returns a bound dispatcher for instance methods, or a dispatcher for static/class methods."""
        return BoundOverloadDispatcher(instance, owner_cls, self.name, self.overloads, self.signatures)

    def __call__(self, *args: Any, **kwargs: Any) -> Any:
        """Calls the function overload dispatcher."""
        return FunctionOverloadDispatcher(self.name, self.overloads, self.signatures)(*args, **kwargs)

    def __len__(self) -> int:
        """Returns the number of overloads."""
        return len(self.overloads)

    def help(self, *args: Any, **kwargs: Any) -> str:
        """Returns the docstring of the best matching overload."""
        func = FunctionOverloadDispatcher(self.name, self.overloads, self.signatures).best_match(*args, **kwargs)
        return func.__doc__ or ""

    @property
    def __doc__(self) -> str:  # type: ignore
        """Returns a docstring with all the overloads."""
        items = "\n".join(f"- {sig}: {f.__doc__ or ''}" for sig, f in zip(self.signatures, self.overloads))
        return f"Overloaded function '{self.name}' with {len(self)} signatures:\n" + items


class OverloadMeta(type):
    """A metaclass that allows overloading methods and functions."""

    @classmethod
    def __prepare__(mcs, _name: str, _bases: Tuple[type, ...], /, **_kwargs: Any) -> OverloadDict:
        """Returns a dictionary that allows overloading."""
        return OverloadDict()

    def __new__(mcs, name: str, bases: tuple, namespace: OverloadDict, **kwargs: Any) -> Any:
        """Creates a new class with overloaded methods and functions."""
        return super().__new__(mcs, name, bases, namespace, **kwargs)


# pylint: disable=too-few-public-methods
class Overload(metaclass=OverloadMeta):
    """A class that allows overloading methods and functions."""


_overload_functions: Dict[str, OverloadItem] = {}
"""A dictionary that maps function names to their overloads. Used by the `overload` decorator."""


def overload(func: Callable) -> Callable:
    """A decorator that allows overloading functions."""
    name = f"{func.__module__}.{func.__qualname__}"
    if name not in _overload_functions:
        _overload_functions[name] = OverloadItem(func)
    else:
        _overload_functions[name].append(func)

    function = _overload_functions[name]
    return function


if __name__ == "__main__":

    class SaysHey(Overload):
        def hello(self, x: int, y: Union[int, str]) -> None:
            pass

    a = SaysHey()
    a.hello(1, 2)
