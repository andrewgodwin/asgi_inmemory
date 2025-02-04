import asyncio
import socket as sock
from functools import partial

import pytest

from asgiref.server import StatelessServer


async def sock_recvfrom(sock, n):
    while True:
        try:
            return sock.recvfrom(n)
        except BlockingIOError:
            await asyncio.sleep(0)


class Server(StatelessServer):
    def __init__(self, application, max_applications=1000):
        super().__init__(
            application,
            max_applications=max_applications,
        )
        self._sock = sock.socket(sock.AF_INET, sock.SOCK_DGRAM)
        self._sock.setblocking(False)
        self._sock.bind(("127.0.0.1", 0))

    @property
    def address(self):
        return self._sock.getsockname()

    async def handle(self):
        while True:
            data, addr = await sock_recvfrom(self._sock, 4096)
            data = data.decode("utf-8")

            if data.startswith("Register"):
                _, usr_name = data.split(" ")
                input_quene = self.get_or_create_application_instance(usr_name, addr)
                input_quene.put_nowait(b"Welcome")

            elif data.startswith("To"):
                _, usr_name, msg = data.split(" ", 2)
                input_quene = self.get_or_create_application_instance(usr_name, addr)
                input_quene.put_nowait(msg.encode("utf-8"))

    async def application_send(self, scope, message):
        self._sock.sendto(message, scope)

    def close(self):
        self._sock.close()
        for details in self.application_instances.values():
            details["future"].cancel()


class Client:
    def __init__(self, name):
        self._sock = sock.socket(sock.AF_INET, sock.SOCK_DGRAM)
        self._sock.setblocking(False)
        self.name = name

    async def register(self, server_addr, name=None):
        name = name or self.name
        self._sock.sendto(f"Register {name}".encode(), server_addr)

    async def send(self, server_addr, to, msg):
        self._sock.sendto(f"To {to} {msg}".encode(), server_addr)

    async def get_msg(self):
        msg, server_addr = await sock_recvfrom(self._sock, 4096)
        return msg, server_addr

    def close(self):
        self._sock.close()


@pytest.fixture(scope="function")
def server():
    async def app(scope, receive, send):
        while True:
            msg = await receive()
            await send(msg)

    server = Server(app, 10)
    yield server
    server.close()


async def check_client_msg(client, expected_address, expected_msg):
    msg, server_addr = await asyncio.wait_for(client.get_msg(), timeout=1.0)
    assert msg == expected_msg
    assert server_addr == expected_address


async def server_auto_close(fut, timeout):
    """Server run based on run_until_complete. It will block forever with handle
    function because it is a while True loop without break.  Use this method to close
    server automatically."""
    loop = asyncio.get_running_loop()
    task = asyncio.ensure_future(fut, loop=loop)
    await asyncio.sleep(timeout)
    task.cancel()


def test_stateless_server(server):
    """StatelessServer can be instantiated with an ASGI 3 application."""
    """Create a UDP Server can register instance based on name from message of client.
    Clients can communicate to other client by name through server"""

    loop = asyncio.new_event_loop()
    asyncio.get_event_loop_policy().set_event_loop(loop)
    server.handle = partial(server_auto_close, fut=server.handle(), timeout=1.0)

    client1 = Client(name="client1")
    client2 = Client(name="client2")

    async def check_client1_behavior():
        await client1.register(server.address)
        await check_client_msg(client1, server.address, b"Welcome")
        await client1.send(server.address, "client2", "Hello")

    async def check_client2_behavior():
        await client2.register(server.address)
        await check_client_msg(client2, server.address, b"Welcome")
        await check_client_msg(client2, server.address, b"Hello")

    task1 = loop.create_task(check_client1_behavior())
    task2 = loop.create_task(check_client2_behavior())

    server.run()

    assert task1.done()
    assert task2.done()


def test_server_delete_instance(server):
    """The max_applications of Server is 10. After 20 times register, application number should be 10."""
    loop = asyncio.new_event_loop()
    asyncio.get_event_loop_policy().set_event_loop(loop)
    server.handle = partial(server_auto_close, fut=server.handle(), timeout=1.0)

    client1 = Client(name="client1")

    async def client1_multiple_register():
        for i in range(20):
            await client1.register(server.address, name=f"client{i}")
            print(f"client{i}")
            await check_client_msg(client1, server.address, b"Welcome")

    task = loop.create_task(client1_multiple_register())
    server.run()

    assert task.done()
