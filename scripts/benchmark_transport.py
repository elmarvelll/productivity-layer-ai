"""Loopback-only transport audit. No provider calls, database access, or real secrets."""
import asyncio
import json
import statistics
import time
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.config import Settings
from app.integrations.akadverse import AkadverseClient


async def main():
    connections = 0
    requests = 0

    async def handle(reader, writer):
        nonlocal connections, requests
        connections += 1
        try:
            while True:
                headers = await reader.readuntil(b'\r\n\r\n')
                length = next(int(line.split(b':', 1)[1]) for line in headers.split(b'\r\n')
                              if line.lower().startswith(b'content-length:'))
                await reader.readexactly(length)
                requests += 1
                body = b'{"result":{"status":"completed"}}'
                writer.write(b'HTTP/1.1 200 OK\r\nContent-Type: application/json\r\nContent-Length: '
                             + str(len(body)).encode() + b'\r\n\r\n' + body)
                await writer.drain()
        except (asyncio.IncompleteReadError, ConnectionError):
            pass
        finally:
            writer.close()
            await writer.wait_closed()

    server = await asyncio.start_server(handle, '127.0.0.1', 0)
    port = server.sockets[0].getsockname()[1]
    settings = Settings(_env_file=None, gemini_api_key='fixture-only',
                        akadverse_api_base_url=f'http://127.0.0.1:{port}',
                        productivity_ai_service_token='fixture-only-token-with-at-least-32-characters',
                        productivity_ai_jwt_public_key='fixture-only-unused-key')
    report = {'scope': 'loopback HTTP fixture; not production latency or model quality', 'callbacks_per_turn': 7, 'rounds': 5}
    async with server:
        for reuse in (False, True):
            timings = []
            before_connections, before_requests = connections, requests
            for _ in range(report['rounds']):
                started = time.perf_counter()
                backend = AkadverseClient(settings, 'fixture-callback-token')
                async def calls():
                    await backend.context()
                    for step in range(6):
                        await backend.tool(step, 'list_tasks', {})
                if reuse:
                    async with backend:
                        await calls()
                else:
                    await calls()
                timings.append(round((time.perf_counter() - started) * 1000, 2))
            report['reused_session' if reuse else 'fresh_sessions'] = {
                'connections': connections - before_connections,
                'requests': requests - before_requests,
                'median_ms': statistics.median(timings), 'samples_ms': timings,
            }
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    asyncio.run(main())
