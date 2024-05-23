import os
import json
import signal
import asyncio
import websockets

ROOMS = {}

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

async def join_room(websocket, room):
    try:
        if room in ROOMS:
            # Room exists, join room
            ROOMS[room]["connected"].add(websocket)
            success_msg = {
                "type": "success",
                "message": f"Joined room {room}"
            }
        else:
            # Room doesnt exist, create room
            ROOMS[room] = {"connected": {websocket}}
            success_msg = {
                "type": "success",
                "message": f"Created room {room}"
            }
            await websocket.send(json.dumps(success_msg))
    finally:
        ROOMS[room]["connected"].remove(websocket)
        if len(ROOMS[room]) == 0: del ROOMS[room]

async def handler(websocket):
    message = await websocket.recv()
    event = json.loads(message)
    assert event["type"] == "init"
    assert "room" in event

    if len(event["room"]) == 5 and event["room"].isalnum():
        await join_room(websocket, event["room"])
    else:
        send_error(websocket, "Invalid room code")

async def main():
    # Set the stop condition when receiving SIGTERM.
    loop = asyncio.get_running_loop()
    stop = loop.create_future()
    loop.add_signal_handler(signal.SIGTERM, stop.set_result, None)

    port = int(os.environ.get("PORT", "8765"))
    print("Starting server!")
    async with websockets.serve(handler, "", port):
        await stop


if __name__ == "__main__":
    asyncio.run(main())
