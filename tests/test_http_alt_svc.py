import sys

from pathlib import Path

import pytest

from sanic.app import Sanic
from sanic.response import empty
from tests.client import RawClient


parent_dir = Path(__file__).parent
localhost_dir = parent_dir / "certs/localhost"


@pytest.mark.skipif(sys.version_info < (3, 9), reason="Not supported in 3.7")
def test_http1_response_has_alt_svc(port):
    Sanic._app_registry.clear()
    app = Sanic("TestAltSvc")
    app.config.TOUCHUP = True
    response = b""

    @app.get("/")
    async def handler(*_):
        return empty()

    @app.after_server_start
    async def do_request(*_):
        nonlocal response

        app.router.reset()
        app.router.finalize()

        client = RawClient(app.state.host, app.state.port)
        await client.connect()
        await client.send(
            """
            GET / HTTP/1.1
            host: localhost:7777

            """
        )
        response = await client.recv(1024)
        await client.close()

    @app.after_server_start
    def shutdown(*_):
        app.stop()

    app.prepare(
        version=3,
        ssl={
            "cert": localhost_dir / "fullchain.pem",
            "key": localhost_dir / "privkey.pem",
        },
        port=port,
    )
    app.prepare(
        version=1,
        port=port,
    )
    Sanic.serve_single(app)

    assert f'alt-svc: h3=":{port}"\r\n'.encode() in response
