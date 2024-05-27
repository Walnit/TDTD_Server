import os
import ssl
import json
import http
import signal
import pathlib
import asyncio
import websockets

ROOMS = {}

#ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
#pem = pathlib.Path(__file__).with_name("cert.pem")
#key = pathlib.Path(__file__).with_name("key.pem")
#ssl_context.load_cert_chain(pem, keyfile=key)

# Game Schema:
{
    "defender": "<P1_SESSION_ID>",
    "defender_name": "<P1_NAME>",
    "attacker": "<P2_SESSION_ID>",
    "attacker_name": "<P2_NAME>"
}

async def send_error(websocket, message):
    error_msg = {
        "type": "error",
        "message": message
    }
    await websocket.send(json.dumps(error_msg))

async def game_process(websocket, room, role):
    async for message in websocket:
        if "started" in ROOMS[room]:
            if role == "attacker":
                await ROOMS[room]["defender"].send(message)
            else:
                await ROOMS[room]["attacker"].send(message)

async def wait_for_start(websocket, room):
    message = await websocket.recv()
    event = json.loads(message)
    assert event["type"] == "ready"
    assert "token" in event

    if event["token"] != ROOMS[room]["attacker_id"] and event["token"] != ROOMS[room]["defender_id"]:
        send_error(websocket, "Invalid token!")
    else:
        if "almostReady" in ROOMS[room]:
            ROOMS[room]["started"] = True
            start_msg = {
                "type": "start"
            }
            websockets.broadcast(ROOMS[room]["connected"], json.dumps(start_msg))
        else:
            ROOMS[room]["almostReady"] = True
        if event["token"] == ROOMS[room]["attacker_id"]:
            ROOMS[room]["attacker"] = websocket
            await game_process(websocket, room, "attacker")
        elif event["token"] == ROOMS[room]["defender_id"]:
            ROOMS[room]["defender"] = websocket
            await game_process(websocket, room, "defender")


async def start_game(room):
    # Randomize roles
    psuedorandomchoice = 0
    for letter in room:
        psuedorandomchoice += ord(letter)
    psuedorandomchoice %= 2 # 0 or 1

    # Get roles
    sockets = list(ROOMS[room]["connected"])
    attacker = sockets[psuedorandomchoice]
    defender = sockets[1-psuedorandomchoice]

    attacker_msg = {
        "type": "role",
        "role": "attacker"
    }
    defender_msg = {
        "type": "role",
        "role": "defender"
    }

    ROOMS[room]["attacker_id"] = attacker.id.hex
    ROOMS[room]["defender_id"] = defender.id.hex

    await attacker.send(json.dumps(attacker_msg))
    await defender.send(json.dumps(defender_msg))

async def join_room(websocket, room):
    try:
        if room in ROOMS:
            # Room exists, join room and start game
            ROOMS[room]["connected"].add(websocket)
            success_msg = {
                "type": "success",
                "message": f"Joined room {room}",
                "token": websocket.id.hex
            }
            await websocket.send(json.dumps(success_msg))
            await start_game(room)
        else:
            # Room doesnt exist, create room
            ROOMS[room] = {"connected": {websocket}}
            success_msg = {
                "type": "success",
                "message": f"Created room {room}",
                "token": websocket.id.hex
            }
            await websocket.send(json.dumps(success_msg))
        await wait_for_start(websocket, room)
    finally:
        ROOMS[room]["connected"].remove(websocket)
        if len(ROOMS[room]["connected"]) == 0:
            del ROOMS[room]
            print("Deleting room", room)


async def handler(websocket):
    try:
        message = await websocket.recv()
        event = json.loads(message)
        assert event["type"] == "init"
        assert "room" in event

        # DEBUG: REMOVE THIS
        print(event)

        if len(event["room"]) == 5 and event["room"].isalnum():
            await join_room(websocket, event["room"])
        else:
            await send_error(websocket, "Invalid room code")
    except websockets.ConnectionClosedOK: pass
    except websockets.exceptions.ConnectionClosedError: print(websocket.id, "didn't close correctly!")

async def health_check(path, request_headers):
    if path == "/health":
        return http.HTTPStatus.OK, [], b"Ok\b"

async def main():
    # Set the stop condition when receiving SIGTERM.
    loop = asyncio.get_running_loop()
    stop = loop.create_future()
    loop.add_signal_handler(signal.SIGTERM, stop.set_result, None)

    port = 8765
    print("Starting server!")
    async with websockets.serve(handler, "", port, process_request=health_check, ssl=None):
        await stop


if __name__ == "__main__":
    asyncio.run(main())
