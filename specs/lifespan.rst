=================
Lifespan Protocol
=================

**Version**: 2.0 (2019-03-20)

The Lifespan ASGI sub-specification outlines how to communicate
lifespan events such as startup and shutdown within ASGI. This refers to the
lifespan of the main event loop. In a multi-process environment there will be
lifespan events in each process. In a multi-thread environment there will be
lifespan events in each thread.

The lifespan messages allow for an application to initialise and
shutdown in the context of a running event loop. An example of this
would be creating a connection pool and subsequently closing the
connection pool to release the connections.

A possible implementation of this protocol is given below::

    database = anyio.lowlevel.RunVar("database")

    async def app(scope, receive, send):
        if scope['type'] == 'lifespan':
            while True:
                message = await receive()
                if message['type'] == 'lifespan.startup':
                    ... # Do some startup here!
                    db = Database()
                    database.set(db)
                    await db.connect()
                    await send({'type': 'lifespan.startup.complete'})
                elif message['type'] == 'lifespan.shutdown':
                    ... # Do some shutdown here!
                    await db.disconnect()
                    await send({'type': 'lifespan.shutdown.complete'})
                    return
        else:
            pass # Handle other types


Scope
'''''

The lifespan scope exists for the duration of the event loop.

The scope information passed in ``scope`` contains basic metadata:

* ``type`` (*Unicode string*) -- ``"lifespan"``.
* ``asgi["version"]`` (*Unicode string*) -- The version of the ASGI spec.
* ``asgi["spec_version"]`` (*Unicode string*) -- The version of this spec being
  used. Optional; if missing defaults to ``"1.0"``.

If an exception is raised when calling the application callable with a
``lifespan.startup`` message or a ``scope`` with type ``lifespan``,
the server must continue but not send any lifespan events.

This allows for compatibility with applications that do not support the
lifespan protocol. If you want to log an error that occurs during lifespan
startup and prevent the server from starting, then send back
``lifespan.startup.failed`` instead.


Startup - ``receive`` event
'''''''''''''''''''''''''''

Sent to the application when the server is ready to startup and receive connections,
but before it has started to do so.

Keys:

* ``type`` (*Unicode string*) -- ``"lifespan.startup"``.


Startup Complete - ``send`` event
'''''''''''''''''''''''''''''''''

Sent by the application when it has completed its startup. A server
must wait for this message before it starts processing connections.

Keys:

* ``type`` (*Unicode string*) -- ``"lifespan.startup.complete"``.


Startup Failed - ``send`` event
'''''''''''''''''''''''''''''''

Sent by the application when it has failed to complete its startup. If a server
sees this it should log/print the message provided and then exit.

Keys:

* ``type`` (*Unicode string*) -- ``"lifespan.startup.failed"``.
* ``message`` (*Unicode string*) -- Optional; if missing defaults to ``""``.


Shutdown - ``receive`` event
''''''''''''''''''''''''''''

Sent to the application when the server has stopped accepting connections and closed
all active connections.

Keys:

* ``type`` (*Unicode string*) --  ``"lifespan.shutdown"``.


Shutdown Complete - ``send`` event
''''''''''''''''''''''''''''''''''

Sent by the application when it has completed its cleanup. A server
must wait for this message before terminating.

Keys:

* ``type`` (*Unicode string*) -- ``"lifespan.shutdown.complete"``.


Shutdown Failed - ``send`` event
''''''''''''''''''''''''''''''''

Sent by the application when it has failed to complete its cleanup. If a server
sees this it should log/print the message provided and then terminate.

Keys:

* ``type`` (*Unicode string*) -- ``"lifespan.shutdown.failed"``.
* ``message`` (*Unicode string*) -- Optional; if missing defaults to ``""``.


Version History
'''''''''''''''

* 2.0 (2019-03-04): Added startup.failed and shutdown.failed,
  clarified exception handling during startup phase.
* 1.0 (2018-09-06): Updated ASGI spec with a lifespan protocol.


Copyright
'''''''''

This document has been placed in the public domain.
