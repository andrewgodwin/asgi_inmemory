import asyncio
import functools
import multiprocessing
import sys
import threading
import time
import warnings
from concurrent.futures import ThreadPoolExecutor
from functools import wraps
from typing import Any
from unittest import TestCase

import pytest

from asgiref.sync import (
    ThreadSensitiveContext,
    async_to_sync,
    iscoroutinefunction,
    sync_to_async,
)
from asgiref.timeout import timeout


@pytest.mark.asyncio
async def test_sync_to_async():
    """
    Tests we can call sync functions from an async thread
    (even if the number of thread workers is less than the number of calls)
    """
    # Define sync function
    def sync_function():
        time.sleep(1)
        return 42

    # Ensure outermost detection works
    # Wrap it
    async_function = sync_to_async(sync_function)
    # Check it works right
    start = time.monotonic()
    result = await async_function()
    end = time.monotonic()
    assert result == 42
    assert end - start >= 1
    # Set workers to 1, call it twice and make sure that works right
    loop = asyncio.get_running_loop()
    old_executor = loop._default_executor or ThreadPoolExecutor()
    loop.set_default_executor(ThreadPoolExecutor(max_workers=1))
    try:
        start = time.monotonic()
        await asyncio.wait(
            [
                asyncio.create_task(async_function()),
                asyncio.create_task(async_function()),
            ]
        )
        end = time.monotonic()
        # It should take at least 2 seconds as there's only one worker.
        assert end - start >= 2
    finally:
        loop.set_default_executor(old_executor)


def test_sync_to_async_fail_non_function():
    """
    async_to_sync raises a TypeError when called with a non-function.
    """
    with pytest.raises(TypeError) as excinfo:
        sync_to_async(1)

    assert excinfo.value.args == (
        "sync_to_async can only be applied to sync functions.",
    )


@pytest.mark.asyncio
async def test_sync_to_async_fail_async():
    """
    sync_to_async raises a TypeError when applied to a sync function.
    """
    with pytest.raises(TypeError) as excinfo:

        @sync_to_async
        async def test_function():
            pass

    assert excinfo.value.args == (
        "sync_to_async can only be applied to sync functions.",
    )


@pytest.mark.asyncio
async def test_async_to_sync_fail_partial():
    """
    sync_to_async raises a TypeError when applied to a sync partial.
    """
    with pytest.raises(TypeError) as excinfo:

        async def test_function(*args):
            pass

        partial_function = functools.partial(test_function, 42)
        sync_to_async(partial_function)

    assert excinfo.value.args == (
        "sync_to_async can only be applied to sync functions.",
    )


@pytest.mark.asyncio
async def test_sync_to_async_raises_typeerror_for_async_callable_instance():
    class CallableClass:
        async def __call__(self):
            return None

    with pytest.raises(
        TypeError, match="sync_to_async can only be applied to sync functions."
    ):
        sync_to_async(CallableClass())


@pytest.mark.asyncio
async def test_sync_to_async_decorator():
    """
    Tests sync_to_async as a decorator
    """
    # Define sync function
    @sync_to_async
    def test_function():
        time.sleep(1)
        return 43

    # Check it works right
    result = await test_function()
    assert result == 43


@pytest.mark.asyncio
async def test_nested_sync_to_async_retains_wrapped_function_attributes():
    """
    Tests that attributes of functions wrapped by sync_to_async are retained
    """

    def enclosing_decorator(attr_value):
        @wraps(attr_value)
        def wrapper(f):
            f.attr_name = attr_value
            return f

        return wrapper

    @enclosing_decorator("test_name_attribute")
    @sync_to_async
    def test_function():
        pass

    assert test_function.attr_name == "test_name_attribute"
    assert test_function.__name__ == "test_function"


@pytest.mark.asyncio
async def test_sync_to_async_method_decorator():
    """
    Tests sync_to_async as a method decorator
    """
    # Define sync function
    class TestClass:
        @sync_to_async
        def test_method(self):
            time.sleep(1)
            return 44

    # Check it works right
    instance = TestClass()
    result = await instance.test_method()
    assert result == 44


@pytest.mark.asyncio
async def test_sync_to_async_method_self_attribute():
    """
    Tests sync_to_async on a method copies __self__
    """

    # Define sync function
    class TestClass:
        def test_method(self):
            time.sleep(0.1)
            return 45

    # Check it works right
    instance = TestClass()
    method = sync_to_async(instance.test_method)
    result = await method()
    assert result == 45

    # Check __self__ has been copied
    assert method.__self__ == instance


@pytest.mark.asyncio
async def test_async_to_sync_to_async():
    """
    Tests we can call async functions from a sync thread created by async_to_sync
    (even if the number of thread workers is less than the number of calls)
    """
    result = {}

    # Define async function
    async def inner_async_function():
        result["worked"] = True
        result["thread"] = threading.current_thread()
        return 65

    # Define sync function
    def sync_function():
        return async_to_sync(inner_async_function)()

    # Wrap it
    async_function = sync_to_async(sync_function)
    # Check it works right
    number = await async_function()
    assert number == 65
    assert result["worked"]
    # Make sure that it didn't needlessly make a new async loop
    assert result["thread"] == threading.current_thread()


@pytest.mark.asyncio
async def test_async_to_sync_to_async_decorator():
    """
    Test async_to_sync as a function decorator uses the outer thread
    when used inside sync_to_async.
    """
    result = {}

    # Define async function
    @async_to_sync
    async def inner_async_function():
        result["worked"] = True
        result["thread"] = threading.current_thread()
        return 42

    # Define sync function
    @sync_to_async
    def sync_function():
        return inner_async_function()

    # Check it works right
    number = await sync_function()
    assert number == 42
    assert result["worked"]
    # Make sure that it didn't needlessly make a new async loop
    assert result["thread"] == threading.current_thread()


@pytest.mark.asyncio
@pytest.mark.skipif(sys.version_info < (3, 9), reason="requires python3.9")
async def test_async_to_sync_to_thread_decorator():
    """
    Test async_to_sync as a function decorator uses the outer thread
    when used inside another sync thread.
    """
    result = {}

    # Define async function
    @async_to_sync
    async def inner_async_function():
        result["worked"] = True
        result["thread"] = threading.current_thread()
        return 42

    # Check it works right
    number = await asyncio.to_thread(inner_async_function)
    assert number == 42
    assert result["worked"]
    # Make sure that it didn't needlessly make a new async loop
    assert result["thread"] == threading.current_thread()


def test_async_to_sync_fail_non_function():
    """
    async_to_sync raises a TypeError when applied to a non-function.
    """
    with pytest.warns(UserWarning) as warnings:
        async_to_sync(1)

    assert warnings[0].message.args == (
        "async_to_sync was passed a non-async-marked callable",
    )


def test_async_to_sync_fail_sync():
    """
    async_to_sync raises a TypeError when applied to a sync function.
    """
    with pytest.warns(UserWarning) as warnings:

        @async_to_sync
        def test_function(self):
            pass

    assert warnings[0].message.args == (
        "async_to_sync was passed a non-async-marked callable",
    )


def test_async_to_sync():
    """
    Tests we can call async_to_sync outside of an outer event loop.
    """
    result = {}

    # Define async function
    async def inner_async_function():
        await asyncio.sleep(0)
        result["worked"] = True
        return 84

    # Run it
    sync_function = async_to_sync(inner_async_function)
    number = sync_function()
    assert number == 84
    assert result["worked"]


def test_async_to_sync_decorator():
    """
    Tests we can call async_to_sync as a function decorator
    """
    result = {}

    # Define async function
    @async_to_sync
    async def test_function():
        await asyncio.sleep(0)
        result["worked"] = True
        return 85

    # Run it
    number = test_function()
    assert number == 85
    assert result["worked"]


def test_async_to_sync_method_decorator():
    """
    Tests we can call async_to_sync as a function decorator
    """
    result = {}

    # Define async function
    class TestClass:
        @async_to_sync
        async def test_function(self):
            await asyncio.sleep(0)
            result["worked"] = True
            return 86

    # Run it
    instance = TestClass()
    number = instance.test_function()
    assert number == 86
    assert result["worked"]


@pytest.mark.asyncio
async def test_async_to_sync_in_async():
    """
    Makes sure async_to_sync bails if you try to call it from an async loop
    """

    # Define async function
    async def inner_async_function():
        return 84

    # Run it
    sync_function = async_to_sync(inner_async_function)
    with pytest.raises(RuntimeError):
        sync_function()


def test_async_to_sync_in_thread():
    """
    Tests we can call async_to_sync inside a thread
    """
    result = {}

    # Define async function
    @async_to_sync
    async def test_function():
        await asyncio.sleep(0)
        result["worked"] = True

    # Make a thread and run it
    thread = threading.Thread(target=test_function)
    thread.start()
    thread.join()
    assert result["worked"]


def test_async_to_sync_in_except():
    """
    Tests we can call async_to_sync inside an except block without it
    re-propagating the exception.
    """

    # Define async function
    @async_to_sync
    async def test_function():
        return 42

    # Run inside except
    try:
        raise ValueError("Boom")
    except ValueError:
        assert test_function() == 42


def test_async_to_sync_partial():
    """
    Tests we can call async_to_sync on an async partial.
    """
    result = {}

    # Define async function
    async def inner_async_function(*args):
        await asyncio.sleep(0)
        result["worked"] = True
        return [*args]

    partial_function = functools.partial(inner_async_function, 42)

    # Run it
    sync_function = async_to_sync(partial_function)
    out = sync_function(84)
    assert out == [42, 84]
    assert result["worked"]


def test_async_to_sync_on_callable_object():
    """
    Tests async_to_sync on a callable class instance
    """

    result = {}

    class CallableClass:
        async def __call__(self, value):
            await asyncio.sleep(0)
            result["worked"] = True
            return value

    # Run it (without warnings)
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        sync_function = async_to_sync(CallableClass())
        out = sync_function(42)

    assert out == 42
    assert result["worked"] is True


def test_async_to_sync_method_self_attribute():
    """
    Tests async_to_sync on a method copies __self__.
    """
    # Define async function.
    class TestClass:
        async def test_function(self):
            await asyncio.sleep(0)
            return 45

    # Check it works right.
    instance = TestClass()
    sync_function = async_to_sync(instance.test_function)
    number = sync_function()
    assert number == 45

    # Check __self__ has been copied.
    assert sync_function.__self__ is instance


def test_thread_sensitive_outside_sync():
    """
    Tests that thread_sensitive SyncToAsync where the outside is sync code runs
    in the main thread.
    """

    result = {}

    # Middle async function
    @async_to_sync
    async def middle():
        await inner()
        await asyncio.create_task(inner_task())

    # Inner sync functions
    @sync_to_async
    def inner():
        result["thread"] = threading.current_thread()

    @sync_to_async
    def inner_task():
        result["thread2"] = threading.current_thread()

    # Run it
    middle()
    assert result["thread"] == threading.current_thread()
    assert result["thread2"] == threading.current_thread()


@pytest.mark.asyncio
async def test_thread_sensitive_outside_async():
    """
    Tests that thread_sensitive SyncToAsync where the outside is async code runs
    in a single, separate thread.
    """

    result_1 = {}
    result_2 = {}

    # Outer sync function
    @sync_to_async
    def outer(result):
        middle(result)

    # Middle async function
    @async_to_sync
    async def middle(result):
        await inner(result)

    # Inner sync function
    @sync_to_async
    def inner(result):
        result["thread"] = threading.current_thread()

    # Run it (in supposed parallel!)
    await asyncio.wait(
        [asyncio.create_task(outer(result_1)), asyncio.create_task(inner(result_2))]
    )

    # They should not have run in the main thread, but in the same thread
    assert result_1["thread"] != threading.current_thread()
    assert result_1["thread"] == result_2["thread"]


@pytest.mark.asyncio
async def test_thread_sensitive_with_context_matches():
    result_1 = {}
    result_2 = {}

    def store_thread(result):
        result["thread"] = threading.current_thread()

    store_thread_async = sync_to_async(store_thread)

    async def fn():
        async with ThreadSensitiveContext():
            # Run it (in supposed parallel!)
            await asyncio.wait(
                [
                    asyncio.create_task(store_thread_async(result_1)),
                    asyncio.create_task(store_thread_async(result_2)),
                ]
            )

    await fn()

    # They should not have run in the main thread, and on the same threads
    assert result_1["thread"] != threading.current_thread()
    assert result_1["thread"] == result_2["thread"]


@pytest.mark.asyncio
async def test_thread_sensitive_nested_context():
    result_1 = {}
    result_2 = {}

    @sync_to_async
    def store_thread(result):
        result["thread"] = threading.current_thread()

    async with ThreadSensitiveContext():
        await store_thread(result_1)
        async with ThreadSensitiveContext():
            await store_thread(result_2)

    # They should not have run in the main thread, and on the same threads
    assert result_1["thread"] != threading.current_thread()
    assert result_1["thread"] == result_2["thread"]


@pytest.mark.asyncio
async def test_thread_sensitive_context_without_sync_work():
    async with ThreadSensitiveContext():
        pass


def test_thread_sensitive_double_nested_sync():
    """
    Tests that thread_sensitive SyncToAsync nests inside itself where the
    outside is sync.
    """

    result = {}

    # Async level 1
    @async_to_sync
    async def level1():
        await level2()

    # Sync level 2
    @sync_to_async
    def level2():
        level3()

    # Async level 3
    @async_to_sync
    async def level3():
        await level4()

    # Sync level 2
    @sync_to_async
    def level4():
        result["thread"] = threading.current_thread()

    # Run it
    level1()
    assert result["thread"] == threading.current_thread()


@pytest.mark.asyncio
async def test_thread_sensitive_double_nested_async():
    """
    Tests that thread_sensitive SyncToAsync nests inside itself where the
    outside is async.
    """

    result = {}

    # Sync level 1
    @sync_to_async
    def level1():
        level2()

    # Async level 2
    @async_to_sync
    async def level2():
        await level3()

    # Sync level 3
    @sync_to_async
    def level3():
        level4()

    # Async level 4
    @async_to_sync
    async def level4():
        result["thread"] = threading.current_thread()

    # Run it
    await level1()
    assert result["thread"] == threading.current_thread()


def test_thread_sensitive_disabled():
    """
    Tests that we can disable thread sensitivity and make things run in
    separate threads.
    """

    result = {}

    # Middle async function
    @async_to_sync
    async def middle():
        await inner()

    # Inner sync function
    @sync_to_async(thread_sensitive=False)
    def inner():
        result["thread"] = threading.current_thread()

    # Run it
    middle()
    assert result["thread"] != threading.current_thread()


class ASGITest(TestCase):
    """
    Tests collection of async cases inside classes
    """

    @async_to_sync
    async def test_wrapped_case_is_collected(self):
        self.assertTrue(True)


def test_sync_to_async_detected_as_coroutinefunction():
    """
    Tests that SyncToAsync functions are detected as coroutines.
    """

    def sync_func():
        return

    assert not iscoroutinefunction(sync_to_async)
    assert iscoroutinefunction(sync_to_async(sync_func))


async def async_process(queue):
    queue.put(42)


def sync_process(queue):
    """Runs async_process synchronously"""
    async_to_sync(async_process)(queue)


def fork_first():
    """Forks process before running sync_process"""
    queue = multiprocessing.Queue()
    fork = multiprocessing.Process(target=sync_process, args=[queue])
    fork.start()
    fork.join(3)
    # Force cleanup in failed test case
    if fork.is_alive():
        fork.terminate()
    return queue.get(True, 1)


@pytest.mark.asyncio
async def test_multiprocessing():
    """
    Tests that a forked process can use async_to_sync without it looking for
    the event loop from the parent process.
    """
    assert await sync_to_async(fork_first)() == 42


@pytest.mark.asyncio
async def test_sync_to_async_uses_executor():
    """
    Tests that SyncToAsync uses the passed in executor correctly.
    """

    class CustomExecutor:
        def __init__(self):
            self.executor = ThreadPoolExecutor(max_workers=1)
            self.times_submit_called = 0

        def submit(self, callable_, *args, **kwargs):
            self.times_submit_called += 1
            return self.executor.submit(callable_, *args, **kwargs)

    expected_result = "expected_result"

    def sync_func():
        return expected_result

    custom_executor = CustomExecutor()
    async_function = sync_to_async(
        sync_func, thread_sensitive=False, executor=custom_executor
    )
    actual_result = await async_function()
    assert actual_result == expected_result
    assert custom_executor.times_submit_called == 1

    pytest.raises(
        TypeError,
        sync_to_async,
        sync_func,
        thread_sensitive=True,
        executor=custom_executor,
    )


def test_sync_to_async_deadlock_ignored_with_exception():
    """
    Ensures that throwing an exception from inside a deadlock-protected block
    still resets the deadlock detector's status.
    """

    def view():
        raise ValueError()

    async def server_entry():
        try:
            await sync_to_async(view)()
        except ValueError:
            pass
        try:
            await sync_to_async(view)()
        except ValueError:
            pass

    asyncio.run(server_entry())


@pytest.mark.asyncio
@pytest.mark.xfail
async def test_sync_to_async_with_blocker_thread_sensitive():
    """
    Tests sync_to_async running on a long-time blocker in a thread_sensitive context.
    Expected to fail at the moment.
    """

    delay = 1  # second
    event = multiprocessing.Event()

    async def async_process_waiting_on_event():
        """Wait for the event to be set."""
        await sync_to_async(event.wait)()
        return 42

    async def async_process_that_triggers_event():
        """Sleep, then set the event."""
        await asyncio.sleep(delay)
        await sync_to_async(event.set)()

    # Run the event setter as a task.
    trigger_task = asyncio.ensure_future(async_process_that_triggers_event())

    try:
        # wait on the event waiter, which is now blocking the event setter.
        async with timeout(delay + 1):
            assert await async_process_waiting_on_event() == 42
    except asyncio.TimeoutError:
        # In case of timeout, set the event to unblock things, else
        # downstream tests will get fouled up.
        event.set()
        raise
    finally:
        await trigger_task


@pytest.mark.asyncio
async def test_sync_to_async_with_blocker_non_thread_sensitive():
    """
    Tests sync_to_async running on a long-time blocker in a non_thread_sensitive context.
    """

    delay = 1  # second
    event = multiprocessing.Event()

    async def async_process_waiting_on_event():
        """Wait for the event to be set."""
        await sync_to_async(event.wait, thread_sensitive=False)()
        return 42

    async def async_process_that_triggers_event():
        """Sleep, then set the event."""
        await asyncio.sleep(1)
        await sync_to_async(event.set)()

    # Run the event setter as a task.
    trigger_task = asyncio.ensure_future(async_process_that_triggers_event())

    try:
        # wait on the event waiter, which is now blocking the event setter.
        async with timeout(delay + 1):
            assert await async_process_waiting_on_event() == 42
    except asyncio.TimeoutError:
        # In case of timeout, set the event to unblock things, else
        # downstream tests will get fouled up.
        event.set()
        raise
    finally:
        await trigger_task


@pytest.mark.asyncio
async def test_sync_to_async_within_create_task():
    """
    Test a stack of sync_to_async/async_to_sync/sync_to_async works even when last
    sync_to_async is wrapped in asyncio.wait_for.
    """
    main_thread = threading.current_thread()
    sync_thread = None

    # Hypothetical Django scenario - middleware function is sync and will run
    # in a new thread created by sync_to_async
    def sync_middleware():
        nonlocal sync_thread
        sync_thread = threading.current_thread()
        assert sync_thread != main_thread
        # View is async and wrapped with async_to_sync.
        async_to_sync(async_view)()

    async def async_view():
        # Call a sync function using sync_to_async, but asyncio.wait_for it
        # rather than directly await it.
        await asyncio.wait_for(sync_to_async(sync_task)(), timeout=1)

    task_executed = False

    def sync_task():
        nonlocal task_executed, sync_thread
        assert sync_thread == threading.current_thread()
        task_executed = True

    async with ThreadSensitiveContext():
        await sync_to_async(sync_middleware)()

    assert task_executed


@pytest.mark.asyncio
async def test_inner_shield_sync_middleware():
    """
    Tests that asyncio.shield is capable of preventing http.disconnect from
    cancelling a django request task when using sync middleware.
    """

    # Hypothetical Django scenario - middleware function is sync
    def sync_middleware():
        async_to_sync(async_view)()

    task_complete = False
    task_cancel_caught = False

    # Future that completes when subtask cancellation attempt is caught
    task_blocker = asyncio.Future()

    async def async_view():
        """Async view with a task that is shielded from cancellation."""
        nonlocal task_complete, task_cancel_caught, task_blocker
        task = asyncio.create_task(async_task())
        try:
            await asyncio.shield(task)
        except asyncio.CancelledError:
            task_cancel_caught = True
            task_blocker.set_result(True)
            await task
            task_complete = True

    task_executed = False

    # Future that completes after subtask is created
    task_started_future = asyncio.Future()

    async def async_task():
        """Async subtask that should not be canceled when parent is canceled."""
        nonlocal task_started_future, task_executed, task_blocker
        task_started_future.set_result(True)
        await task_blocker
        task_executed = True

    task_cancel_propagated = False

    async with ThreadSensitiveContext():
        task = asyncio.create_task(sync_to_async(sync_middleware)())
        await task_started_future
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            task_cancel_propagated = True
        assert not task_cancel_propagated
        assert task_cancel_caught
        assert task_complete

    assert task_executed


@pytest.mark.asyncio
async def test_inner_shield_async_middleware():
    """
    Tests that asyncio.shield is capable of preventing http.disconnect from
    cancelling a django request task when using async middleware.
    """

    # Hypothetical Django scenario - middleware function is async
    async def async_middleware():
        await async_view()

    task_complete = False
    task_cancel_caught = False

    # Future that completes when subtask cancellation attempt is caught
    task_blocker = asyncio.Future()

    async def async_view():
        """Async view with a task that is shielded from cancellation."""
        nonlocal task_complete, task_cancel_caught, task_blocker
        task = asyncio.create_task(async_task())
        try:
            await asyncio.shield(task)
        except asyncio.CancelledError:
            task_cancel_caught = True
            task_blocker.set_result(True)
            await task
            task_complete = True

    task_executed = False

    # Future that completes after subtask is created
    task_started_future = asyncio.Future()

    async def async_task():
        """Async subtask that should not be canceled when parent is canceled."""
        nonlocal task_started_future, task_executed, task_blocker
        task_started_future.set_result(True)
        await task_blocker
        task_executed = True

    task_cancel_propagated = False

    async with ThreadSensitiveContext():
        task = asyncio.create_task(async_middleware())
        await task_started_future
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            task_cancel_propagated = True
        assert not task_cancel_propagated
        assert task_cancel_caught
        assert task_complete

    assert task_executed


@pytest.mark.asyncio
async def test_inner_shield_sync_and_async_middleware():
    """
    Tests that asyncio.shield is capable of preventing http.disconnect from
    cancelling a django request task when using sync and middleware chained
    together.
    """

    # Hypothetical Django scenario - middleware function is sync
    def sync_middleware_1():
        async_to_sync(async_middleware_2)()

    # Hypothetical Django scenario - middleware function is async
    async def async_middleware_2():
        await sync_to_async(sync_middleware_3)()

    # Hypothetical Django scenario - middleware function is sync
    def sync_middleware_3():
        async_to_sync(async_middleware_4)()

    # Hypothetical Django scenario - middleware function is async
    async def async_middleware_4():
        await sync_to_async(sync_middleware_5)()

    # Hypothetical Django scenario - middleware function is sync
    def sync_middleware_5():
        async_to_sync(async_view)()

    task_complete = False
    task_cancel_caught = False

    # Future that completes when subtask cancellation attempt is caught
    task_blocker = asyncio.Future()

    async def async_view():
        """Async view with a task that is shielded from cancellation."""
        nonlocal task_complete, task_cancel_caught, task_blocker
        task = asyncio.create_task(async_task())
        try:
            await asyncio.shield(task)
        except asyncio.CancelledError:
            task_cancel_caught = True
            task_blocker.set_result(True)
            await task
            task_complete = True

    task_executed = False

    # Future that completes after subtask is created
    task_started_future = asyncio.Future()

    async def async_task():
        """Async subtask that should not be canceled when parent is canceled."""
        nonlocal task_started_future, task_executed, task_blocker
        task_started_future.set_result(True)
        await task_blocker
        task_executed = True

    task_cancel_propagated = False

    async with ThreadSensitiveContext():
        task = asyncio.create_task(sync_to_async(sync_middleware_1)())
        await task_started_future
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            task_cancel_propagated = True
        assert not task_cancel_propagated
        assert task_cancel_caught
        assert task_complete

    assert task_executed


@pytest.mark.asyncio
async def test_inner_shield_sync_and_async_middleware_sync_task():
    """
    Tests that asyncio.shield is capable of preventing http.disconnect from
    cancelling a django request task when using sync and middleware chained
    together with an async view calling a sync function calling an async task.

    This test ensures that a parent initiated task cancellation will not
    propagate to a shielded subtask.
    """

    # Hypothetical Django scenario - middleware function is sync
    def sync_middleware_1():
        async_to_sync(async_middleware_2)()

    # Hypothetical Django scenario - middleware function is async
    async def async_middleware_2():
        await sync_to_async(sync_middleware_3)()

    # Hypothetical Django scenario - middleware function is sync
    def sync_middleware_3():
        async_to_sync(async_middleware_4)()

    # Hypothetical Django scenario - middleware function is async
    async def async_middleware_4():
        await sync_to_async(sync_middleware_5)()

    # Hypothetical Django scenario - middleware function is sync
    def sync_middleware_5():
        async_to_sync(async_view)()

    task_complete = False
    task_cancel_caught = False

    # Future that completes when subtask cancellation attempt is caught
    task_blocker = asyncio.Future()

    async def async_view():
        """Async view with a task that is shielded from cancellation."""
        nonlocal task_complete, task_cancel_caught, task_blocker
        task = asyncio.create_task(sync_to_async(sync_parent)())
        try:
            await asyncio.shield(task)
        except asyncio.CancelledError:
            task_cancel_caught = True
            task_blocker.set_result(True)
            await task
            task_complete = True

    task_executed = False

    # Future that completes after subtask is created
    task_started_future = asyncio.Future()

    def sync_parent():
        async_to_sync(async_task)()

    async def async_task():
        """Async subtask that should not be canceled when parent is canceled."""
        nonlocal task_started_future, task_executed, task_blocker
        task_started_future.set_result(True)
        await task_blocker
        task_executed = True

    task_cancel_propagated = False

    async with ThreadSensitiveContext():
        task = asyncio.create_task(sync_to_async(sync_middleware_1)())
        await task_started_future
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            task_cancel_propagated = True
        assert not task_cancel_propagated
        assert task_cancel_caught
        assert task_complete

    assert task_executed


def test_async_to_sync_overlapping_kwargs() -> None:
    """
    Tests that AsyncToSync correctly passes through kwargs to the wrapped function,
    particularly in the case where the wrapped function uses same names for the parameters
    as the wrapper.
    """

    @async_to_sync
    async def test_function(**kwargs: Any) -> None:
        assert kwargs

    # AsyncToSync.main_wrap has a param named `context`.
    # So we pass the same argument here to test for the error
    # "AsyncToSync.main_wrap() got multiple values for argument '<kwarg>'"
    test_function(context=1)


@pytest.mark.asyncio
async def test_sync_to_async_overlapping_kwargs() -> None:
    """
    Tests that SyncToAsync correctly passes through kwargs to the wrapped function,
    particularly in the case where the wrapped function uses same names for the parameters
    as the wrapper.
    """

    @sync_to_async
    def test_function(**kwargs: Any) -> None:
        assert kwargs

    # SyncToAsync.__call__.loop.run_in_executor has a param named `task_context`.
    await test_function(task_context=1)


def test_nested_task() -> None:
    async def inner() -> asyncio.Task[None]:
        return asyncio.create_task(sync_to_async(print)("inner"))

    async def main() -> None:
        task = await sync_to_async(async_to_sync(inner))()
        await task

    async_to_sync(main)()


def test_nested_task_later() -> None:
    def later(fut: asyncio.Future[asyncio.Task[None]]) -> None:
        task = asyncio.create_task(sync_to_async(print)("later"))
        fut.set_result(task)

    async def inner() -> asyncio.Future[asyncio.Task[None]]:
        loop = asyncio.get_running_loop()
        fut = loop.create_future()
        loop.call_later(0.1, later, fut)
        return fut

    async def main() -> None:
        fut = await sync_to_async(async_to_sync(inner))()
        task = await fut
        await task

    async_to_sync(main)()
