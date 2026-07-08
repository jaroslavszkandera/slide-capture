import functools
import time
from typing import Callable, ParamSpec, TypeVar

P = ParamSpec("P")  # params of the function being decorated
T = TypeVar("T")  # return type of the function being decorated


def timer(func: Callable[P, T]) -> Callable[P, T]:
    """
    Print the runtime of the decorated function
    """

    @functools.wraps(func)
    def wrapper_timer(*args: P.args, **kwargs: P.kwargs) -> T:
        start_time: float = time.perf_counter()
        value: T = func(*args, **kwargs)
        end_time: float = time.perf_counter()
        run_time: float = end_time - start_time
        print(f"Finished {func.__name__}() in {run_time:.3f} s")
        return value

    return wrapper_timer


def debug(func: Callable[P, T]) -> Callable[P, T]:
    """
    Print the function signature and return value
    """

    @functools.wraps(func)
    def wrapper_debug(*args: P.args, **kwargs: P.kwargs) -> T:
        args_repr: list[str] = [repr(a) for a in args]
        kwargs_repr: list[str] = [f"{k}={repr(v)}" for k, v in kwargs.items()]
        signature: str = ", ".join(args_repr + kwargs_repr)

        print(f"Calling {func.__name__}({signature})")
        value: T = func(*args, **kwargs)
        print(f"{func.__name__}() returned {repr(value)}")

        return value

    return wrapper_debug
