import json
import pytest
import asyncio
import websockets

test_uri = "ws://localhost:8765"

async def server():
    return websockets.connect(test_uri)

@pytest.mark.dependency()
@pytest.mark.asyncio
async def test_server_started():
    async with await server() as websocket:
        assert await websocket.ping()

def require_server(func):
    depend_deco = pytest.mark.dependency(depends=["test_server_started"])
    async_deco = pytest.mark.asyncio()

    return depend_deco(async_deco(func))

@require_server
async def test_create_room():
    async with await server() as websocket:
        create_room_request = {
            "type": "init",
            "room": "ABCDE"
        }
        await websocket.send(json.dumps(create_room_request))
        result = json.loads(await websocket.recv())
        assert result["message"] == "Created room ABCDE"

@require_server
async def test_invalid_room_len():
    async with await server() as websocket:
        create_room_request = {
            "type": "init",
            "room": "123456"
        }
        await websocket.send(json.dumps(create_room_request))
        result = json.loads(await websocket.recv())
        assert result["message"] == "Invalid room code"

@require_server
async def test_invalid_room_chars():
    async with await server() as websocket:
        create_room_request = {
            "type": "init",
            "room": "HE@RT"
        }
        await websocket.send(json.dumps(create_room_request))
        result = json.loads(await websocket.recv())
        assert result["message"] == "Invalid room code"


@require_server
async def test_invalid_room_len_and_chars():
    async with await server() as websocket:
        create_room_request = {
            "type": "init",
            "room": "@B3D$F"
        }
        await websocket.send(json.dumps(create_room_request))
        result = json.loads(await websocket.recv())
        assert result["message"] == "Invalid room code"

@require_server
async def test_invalid_connection_type():
    async with await server() as websocket:
        create_room_request = {
            "type": "wrong",
            "room": "ABCDE"
        }
        await websocket.send(json.dumps(create_room_request))
        with pytest.raises(websockets.exceptions.ConnectionClosedError):
            await websocket.recv()

@require_server
async def test_join_room():
    ws1 = await (await server())
    ws2 = await (await server())

    request = {
        "type": "init",
        "room": "ABCDE"
    }
    await ws1.send(json.dumps(request))
    await ws1.recv()
    await ws2.send(json.dumps(request))
    result = json.loads(await ws2.recv())
    assert result["message"] == "Joined room ABCDE"
    await ws1.close()
    await ws2.close()

@require_server
async def test_create_two_rooms():
    ws1 = await (await server())
    ws2 = await (await server())

    room_1_request = {
        "type": "init",
        "room": "ABCDE"
    }
    room_2_request = {
        "type": "init",
        "room": "12345"
    }

    await ws1.send(json.dumps(room_1_request))
    assert json.loads(await ws1.recv())["message"] == "Created room ABCDE"
    await ws2.send(json.dumps(room_2_request))
    await ws1.close()
    await ws2.close()
