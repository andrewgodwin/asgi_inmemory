import sys

import pytest

from asgiref.testing import ApplicationCommunicator
from asgiref.wsgi import WsgiToAsgi, WsgiToAsgiInstance


@pytest.mark.asyncio
async def test_basic_wsgi():
    """
    Makes sure the WSGI wrapper has basic functionality.
    """

    # Define WSGI app
    def wsgi_application(environ, start_response):
        assert environ["HTTP_TEST_HEADER"] == "test value 1,test value 2"
        start_response("200 OK", [["X-Colour", "Blue"]])
        yield b"first chunk "
        yield b"second chunk"

    # Wrap it
    application = WsgiToAsgi(wsgi_application)
    # Launch it as a test application
    instance = ApplicationCommunicator(
        application,
        {
            "type": "http",
            "http_version": "1.0",
            "method": "GET",
            "path": "/foo/",
            "query_string": b"bar=baz",
            "headers": [
                [b"test-header", b"test value 1"],
                [b"test-header", b"test value 2"],
            ],
        },
    )
    await instance.send_input({"type": "http.request"})
    # Check they send stuff
    assert (await instance.receive_output(1)) == {
        "type": "http.response.start",
        "status": 200,
        "headers": [(b"x-colour", b"Blue")],
    }
    assert (await instance.receive_output(1)) == {
        "type": "http.response.body",
        "body": b"first chunk ",
        "more_body": True,
    }
    assert (await instance.receive_output(1)) == {
        "type": "http.response.body",
        "body": b"second chunk",
        "more_body": True,
    }
    assert (await instance.receive_output(1)) == {"type": "http.response.body"}


def test_script_name():
    scope = {
        "type": "http",
        "http_version": "1.0",
        "method": "GET",
        "root_path": "/base",
        "path": "/base/foo/",
        "query_string": b"bar=baz",
        "headers": [
            [b"test-header", b"test value 1"],
            [b"test-header", b"test value 2"],
        ],
    }
    adapter = WsgiToAsgiInstance(None)
    adapter.scope = scope
    environ = adapter.build_environ(scope, None)
    assert environ["SCRIPT_NAME"] == "/base"
    assert environ["PATH_INFO"] == "/foo/"


@pytest.mark.asyncio
async def test_wsgi_path_encoding():
    """
    Makes sure the WSGI wrapper has basic functionality.
    """

    # Define WSGI app
    def wsgi_application(environ, start_response):
        assert environ["SCRIPT_NAME"] == "/中国".encode().decode("latin-1")
        assert environ["PATH_INFO"] == "/中文".encode().decode("latin-1")
        start_response("200 OK", [])
        yield b""

    # Wrap it
    application = WsgiToAsgi(wsgi_application)
    # Launch it as a test application
    instance = ApplicationCommunicator(
        application,
        {
            "type": "http",
            "http_version": "1.0",
            "method": "GET",
            "path": "/中文",
            "root_path": "/中国",
            "query_string": b"bar=baz",
            "headers": [],
        },
    )
    await instance.send_input({"type": "http.request"})
    # Check they send stuff
    assert (await instance.receive_output(1)) == {
        "type": "http.response.start",
        "status": 200,
        "headers": [],
    }
    assert (await instance.receive_output(1)) == {
        "type": "http.response.body",
        "body": b"",
        "more_body": True,
    }
    assert (await instance.receive_output(1)) == {"type": "http.response.body"}


@pytest.mark.asyncio
async def test_wsgi_empty_body():
    """
    Makes sure WsgiToAsgi handles an empty body response correctly
    """

    def wsgi_application(environ, start_response):
        start_response("200 OK", [])
        return []

    application = WsgiToAsgi(wsgi_application)
    instance = ApplicationCommunicator(
        application,
        {
            "type": "http",
            "http_version": "1.0",
            "method": "GET",
            "path": "/",
            "query_string": b"",
            "headers": [],
        },
    )
    await instance.send_input({"type": "http.request"})

    # response.start should always be send
    assert (await instance.receive_output(1)) == {
        "type": "http.response.start",
        "status": 200,
        "headers": [],
    }

    assert (await instance.receive_output(1)) == {"type": "http.response.body"}


@pytest.mark.asyncio
async def test_wsgi_clamped_body():
    """
    Makes sure WsgiToAsgi clamps a body response longer than Content-Length
    """

    def wsgi_application(environ, start_response):
        start_response("200 OK", [("Content-Length", "8")])
        return [b"0123", b"45", b"6789"]

    application = WsgiToAsgi(wsgi_application)
    instance = ApplicationCommunicator(
        application,
        {
            "type": "http",
            "http_version": "1.0",
            "method": "GET",
            "path": "/",
            "query_string": b"",
            "headers": [],
        },
    )
    await instance.send_input({"type": "http.request"})
    assert (await instance.receive_output(1)) == {
        "type": "http.response.start",
        "status": 200,
        "headers": [(b"content-length", b"8")],
    }
    assert (await instance.receive_output(1)) == {
        "type": "http.response.body",
        "body": b"0123",
        "more_body": True,
    }
    assert (await instance.receive_output(1)) == {
        "type": "http.response.body",
        "body": b"45",
        "more_body": True,
    }
    assert (await instance.receive_output(1)) == {
        "type": "http.response.body",
        "body": b"67",
        "more_body": True,
    }
    assert (await instance.receive_output(1)) == {"type": "http.response.body"}


@pytest.mark.asyncio
async def test_wsgi_stops_iterating_after_content_length_bytes():
    """
    Makes sure WsgiToAsgi does not iterate after than Content-Length bytes
    """

    def wsgi_application(environ, start_response):
        start_response("200 OK", [("Content-Length", "4")])
        yield b"0123"
        pytest.fail("WsgiToAsgi should not iterate after Content-Length bytes")
        yield b"4567"

    application = WsgiToAsgi(wsgi_application)
    instance = ApplicationCommunicator(
        application,
        {
            "type": "http",
            "http_version": "1.0",
            "method": "GET",
            "path": "/",
            "query_string": b"",
            "headers": [],
        },
    )
    await instance.send_input({"type": "http.request"})
    assert (await instance.receive_output(1)) == {
        "type": "http.response.start",
        "status": 200,
        "headers": [(b"content-length", b"4")],
    }
    assert (await instance.receive_output(1)) == {
        "type": "http.response.body",
        "body": b"0123",
        "more_body": True,
    }
    assert (await instance.receive_output(1)) == {"type": "http.response.body"}


@pytest.mark.asyncio
async def test_wsgi_multiple_start_response():
    """
    Makes sure WsgiToAsgi only keep Content-Length from the last call to start_response
    """

    def wsgi_application(environ, start_response):
        start_response("200 OK", [("Content-Length", "5")])
        try:
            raise ValueError("Application Error")
        except ValueError:
            start_response("500 Server Error", [], sys.exc_info())
            return [b"Some long error message"]

    application = WsgiToAsgi(wsgi_application)
    instance = ApplicationCommunicator(
        application,
        {
            "type": "http",
            "http_version": "1.0",
            "method": "GET",
            "path": "/",
            "query_string": b"",
            "headers": [],
        },
    )
    await instance.send_input({"type": "http.request"})
    assert (await instance.receive_output(1)) == {
        "type": "http.response.start",
        "status": 500,
        "headers": [],
    }
    assert (await instance.receive_output(1)) == {
        "type": "http.response.body",
        "body": b"Some long error message",
        "more_body": True,
    }
    assert (await instance.receive_output(1)) == {"type": "http.response.body"}


@pytest.mark.asyncio
@pytest.mark.parametrize("has_content_length", [True, False])
async def test_wsgi_multi_body(has_content_length):
    """
    Verify that multiple http.request events with body parts are all delivered
    to the WSGI application.
    """

    def wsgi_application(environ, start_response):
        infp = environ["wsgi.input"]
        if has_content_length:
            # this wsgi application reads the content length header and operates on that
            body = infp.read(12)
        else:
            # this wsgi application supports [wsgi.input_terminated](https://gist.github.com/mitsuhiko/5721547)
            # and reads until EOF.
            assert environ["wsgi.input_terminated"]
            body = infp.read()
        assert body == b"Hello World!"
        start_response("200 OK", [])
        return []

    application = WsgiToAsgi(wsgi_application)
    instance = ApplicationCommunicator(
        application,
        {
            "type": "http",
            "http_version": "1.0",
            "method": "POST",
            "path": "/",
            "query_string": b"",
            "headers": [[b"content-length", b"12"]],
        },
    )
    await instance.send_input(
        {"type": "http.request", "body": b"Hello ", "more_body": True}
    )
    await instance.send_input({"type": "http.request", "body": b"World!"})

    assert (await instance.receive_output(1)) == {
        "type": "http.response.start",
        "status": 200,
        "headers": [],
    }

    assert (await instance.receive_output(1)) == {"type": "http.response.body"}
