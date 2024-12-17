import inspect
from typing import Any, Callable, Coroutine, Optional

from .sync import iscoroutinefunction


def is_double_callable(
    application: Callable[..., Optional[Callable[[], Coroutine[Any, Any, None]]]]
) -> bool:
    """
    Tests to see if an application is a legacy-style (double-callable) application.
    """
    # Look for a hint on the object first
    if getattr(application, "_asgi_single_callable", False):
        return False
    if getattr(application, "_asgi_double_callable", False):
        return True
    # Uninstantiated classes are double-callable
    if inspect.isclass(application):
        return True
    # Instantiated classes depend on their __call__
    if hasattr(application, "__call__"):
        # We only check to see if its __call__ is a coroutine function -
        # if it's not, it still might be a coroutine function itself.
        if iscoroutinefunction(application.__call__):
            return False
    # Non-classes we just check directly
    return not iscoroutinefunction(application)


def double_to_single_callable(
    application: Callable[..., Callable[[], Coroutine[Any, Any, None]]]
) -> Callable[
    [dict[str, Any], Callable[[], Any], Callable[[Any], None]],
    Coroutine[Any, Any, None],
]:
    """
    Transforms a double-callable ASGI application into a single-callable one.
    """

    async def new_application(
        scope: dict[str, Any], receive: Callable[[], Any], send: Callable[[Any], None]
    ) -> None:
        instance = application(scope)
        await instance(receive, send)

    return new_application


def guarantee_single_callable(
    application: Callable[..., Optional[Callable[[], Coroutine[Any, Any, None]]]]
) -> Callable[
    [dict[str, Any], Callable[[], Any], Callable[[Any], None]],
    Coroutine[Any, Any, None],
]:
    """
    Takes either a single- or double-callable application and always returns it
    in single-callable style. Use this to add backward compatibility for ASGI
    2.0 applications to your server/test harness/etc.
    """
    if is_double_callable(application):
        application = double_to_single_callable(application)
    return application
