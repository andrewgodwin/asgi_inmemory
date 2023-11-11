===============
Implementations
===============

Complete or upcoming implementations of ASGI - servers, frameworks, and other
useful pieces.

Servers
=======

Daphne
------

*Stable* / http://github.com/django/daphne

The current ASGI reference server, written in Twisted and maintained as part
of the Django Channels project. Supports HTTP/1, HTTP/2, and WebSockets.


Uvicorn
-------

*Stable* / https://www.uvicorn.org/

A fast ASGI server based on uvloop and httptools.
Supports HTTP/1 and WebSockets.


Hypercorn
---------

*Beta* / https://pgjones.gitlab.io/hypercorn/index.html

An ASGI server based on the sans-io hyper, h11, h2, and wsproto libraries.
Supports HTTP/1, HTTP/2, and WebSockets.


Granian
---------

*Beta* / https://github.com/emmett-framework/granian

A Rust HTTP server for Python applications.
Supports ASGI/3, RSGI and WSGI interface applications.


NGINX Unit
---------

*Stable* / https://unit.nginx.org/configuration/#configuration-python

Unit is a lightweight and versatile open-source server that has three core capabilities: it is a web server for static media assets, an application server that runs code in multiple languages, and a reverse proxy.


Application Frameworks
======================

Django/Channels
---------------

*Stable* / http://channels.readthedocs.io

Channels is the Django project to add asynchronous support to Django and is the
original driving force behind the ASGI project. Supports HTTP and WebSockets
with Django integration, and any protocol with ASGI-native code.


FastAPI
-------

*Beta* / https://github.com/tiangolo/fastapi

FastAPI is an ASGI web framework (made with Starlette) for building web APIs based on
standard Python type annotations and standards like OpenAPI, JSON Schema, and OAuth2.
Supports HTTP and WebSockets.


Flama
-----

*Stable* / https://github.com/vortico/flama

Flama is a data-science oriented framework to rapidly build modern and robust machine 
learning (ML) APIs. The main aim of the framework is to make ridiculously simple the 
deployment of ML APIs. With Flama, data scientists can now quickly turn their ML models 
into asynchronous, auto-documented APIs with just a single line of code. All in just few 
seconds!

Flama comes with an intuitive CLI, and provides an easy-to-learn philosophy to speed up 
the building of highly performant GraphQL, REST, and ML APIs. Besides, it comprises an 
ideal solution for the development of asynchronous and production-ready services, 
offering automatic deployment for ML models. 


Quart
-----

*Beta* / https://github.com/pgjones/quart

Quart is a Python ASGI web microframework. It is intended to provide the easiest
way to use asyncio functionality in a web context, especially with existing Flask apps.
Supports HTTP.


Sanic
-----

*Beta* / https://sanicframework.org

Sanic is an unopinionated and flexible web application server and framework that also
has the ability to operate as an ASGI compatible framework. Therefore, it can be run
using any of the ASGI web servers. Supports HTTP and WebSockets.

Starlette
---------

*Beta* / https://github.com/encode/starlette

Starlette is a minimalist ASGI library for writing against basic but powerful
``Request`` and ``Response`` classes. Supports HTTP and WebSockets.


rpc.py
------

*Beta* / https://github.com/abersheeran/rpc.py

An easy-to-use and powerful RPC framework. RPC server base on WSGI & ASGI, client base 
on ``httpx``. Supports synchronous functions, asynchronous functions, synchronous 
generator functions, and asynchronous generator functions. Optional use of Type hint 
for type conversion. Optional OpenAPI document generation.


Litestar
---------------

*Stable* / https://litestar.dev/

Litestar is a powerful, performant, flexible and opinionated ASGI framework, offering 
first class typing support and a full Pydantic integration. Effortlessly Build Performant 
APIs. 


BlackSheep
---------

*Stable* / https://github.com/Neoteroi/BlackSheep

BlackSheep is typed, fast, minimal web framework. It has performant HTTP client,
flexible dependency injection model, OpenID Connect integration, automatic
OpenAPI documentation, dedicated test client and excellent authentication and
authorization policy implementation. Supports HTTP and WebSockets.


Connexion
---------

*Stable* / https://github.com/spec-first/connexion

Connexion is a modern Python web framework that makes spec-first and API-first development 
easy. You describe your API in an OpenAPI (or Swagger) specification with as much detail 
as you want and Connexion will guarantee that it works as you specified.

You can use Connexion either standalone, or in combination with any ASGI or WSGI-compatible 
framework!


Tools
=====

a2wsgi
------

*Stable* / https://github.com/abersheeran/a2wsgi

Convert WSGI application to ASGI application or ASGI application to WSGI application. 
Pure Python. Only depend on the standard library.
