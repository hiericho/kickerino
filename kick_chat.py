# kick_chat.py
import asyncio
import websockets
import json
import traceback 
import socket # For socket.gaierror
from typing import Callable

KICK_PUSHER_APP_KEY = "32cbd69e4b950bf97679" # Your updated key
PUSHER_URL = f"wss://ws-us2.pusher.com/app/{KICK_PUSHER_APP_KEY}?protocol=7&client=js&version=8.4.0-rc2&flash=false" # Your updated URL
async def listen_to_kick_chat(chatroom_id: int, message_callback: Callable):
    uri = PUSHER_URL
    print(f"Attempting to connect to WebSocket: {uri} for chatroom_id: {chatroom_id}")
    try:
        async with websockets.connect(uri, open_timeout=10) as websocket: # Added open_timeout
            await message_callback({"type": "system", "data": f"Connected to Pusher (Host: ws-us2.pusher.com) for chatroom {chatroom_id}"})

            subscribe_payload = {
                "event": "pusher:subscribe",
                "data": {
                    "auth": "", 
                    "channel": f"chatrooms.{chatroom_id}.v2"
                }
            }
            await websocket.send(json.dumps(subscribe_payload))

            while True:
                try:
                    message_raw = await asyncio.wait_for(websocket.recv(), timeout=60) # Added recv timeout
                    message_data = json.loads(message_raw)
                    
                    event_name = message_data.get("event")

                    if event_name == "pusher:subscription_succeeded":
                        await message_callback({"type": "system", "data": f"Subscribed to {message_data.get('channel')}"})
                    elif event_name == "pusher:ping":
                        await websocket.send(json.dumps({"event":"pusher:pong","data":{}}))
                    elif event_name == "pusher:connection_established":
                        socket_id = json.loads(message_data.get("data", "{}")).get("socket_id")
                        await message_callback({"type": "system", "data": f"Pusher connection established. Socket ID: {socket_id}"})
                    elif event_name == "App\\Events\\ChatMessageEvent":
                        chat_message_json_str = message_data.get("data")
                        if chat_message_json_str:
                            chat_message = json.loads(chat_message_json_str)
                            await message_callback({"type": "chat", "data": chat_message})
                    # else: # Optional: Log unhandled events
                    #     if event_name and not event_name.startswith("pusher:internal"):
                    #         print(f"Unhandled Pusher event: {event_name} - Data: {message_data.get('data')}")

                except asyncio.TimeoutError: # Timeout on recv()
                    # print(f"WebSocket recv timeout for chatroom {chatroom_id}, sending keepalive ping...")
                    try:
                        # Send a Pusher ping to see if connection is still alive, or our own if needed
                        # await websocket.ping() # Standard WebSocket ping
                        # Pusher might expect its own ping/pong, but ponging to their ping is usually enough
                        pass # Rely on server pings for now
                    except websockets.exceptions.ConnectionClosed:
                        print(f"Connection closed while trying to send keepalive ping for chatroom {chatroom_id}.")
                        break # Break from while loop
                except websockets.exceptions.ConnectionClosed as e_closed_inner:
                    print(f"WebSocket connection closed during recv loop (Chatroom {chatroom_id}): {e_closed_inner}")
                    await message_callback({"type": "error", "data": f"Chat disconnected: {e_closed_inner.reason} (Code: {e_closed_inner.code})"})
                    break 
                except json.JSONDecodeError as e_json:
                    print(f"JSON Decode Error (Chatroom {chatroom_id}): {message_raw} - Error: {e_json}")
                except Exception as e_inner_loop:
                    print(f"Error in WebSocket recv loop (Chatroom {chatroom_id}): {e_inner_loop}")
                    traceback.print_exc()


    except websockets.exceptions.InvalidURI as e_uri:
        print(f"Invalid WebSocket URI: {uri} - Error: {e_uri}")
        await message_callback({"type": "error", "data": f"Invalid chat server URI."})
    except websockets.exceptions.ConnectionClosedOK as e_closed_ok: # Should be caught by inner loop's ConnectionClosed
        print(f"WebSocket connection closed OK (Chatroom {chatroom_id}): {e_closed_ok}")
        await message_callback({"type": "system", "data": f"Chat connection closed."})
    except websockets.exceptions.ConnectionClosedError as e_closed_err: # Should be caught by inner loop's ConnectionClosed
        print(f"WebSocket connection closed with error (Chatroom {chatroom_id}): {e_closed_err}")
        await message_callback({"type": "error", "data": f"Chat connection error: {e_closed_err.reason} (Code: {e_closed_err.code})"})
    except socket.gaierror as e_gaierror: 
        print(f"DNS Resolution Error (gaierror) for {uri}: {e_gaierror}")
        await message_callback({"type": "error", "data": f"Cannot resolve chat server: {e_gaierror}."})
    except ConnectionRefusedError as e_conn_refused:
        print(f"Connection refused for {uri}: {e_conn_refused}")
        await message_callback({"type": "error", "data": f"Chat server refused connection."})
    except asyncio.TimeoutError as e_timeout: # Timeout on connect()
        print(f"Connection timed out for {uri}: {e_timeout}")
        await message_callback({"type": "error", "data": f"Chat connection timed out."})
    except asyncio.CancelledError:
        print(f"Chat listener task for chatroom {chatroom_id} cancelled.")
        await message_callback({"type": "system", "data": "Chat disconnected (cancelled)."}) # Notify UI
    except Exception as e:
        print(f"General WebSocket error connecting to {uri} (Chatroom {chatroom_id}): {e}")
        traceback.print_exc()
        await message_callback({"type": "error", "data": f"Chat connection error: {e}"})

if __name__ == "__main__":
    async def main_test_chat():
        import aiohttp 
        from kick_api import get_channel_info 

        temp_channel_slug = "xqc" 
        print(f"--- Chat Test for channel: {temp_channel_slug} ---")
        
        async def simple_test_callback(message_obj):
            if message_obj["type"] == "chat":
                message = message_obj["data"]
                sender = message.get("sender", {}).get("username", "Unknown")
                content = message.get("content", "")
                print(f"CHAT >> {sender}: {content}")
            elif message_obj["type"] == "system":
                print(f"SYSTEM >> {message_obj['data']}")
            elif message_obj["type"] == "error":
                print(f"ERROR >> {message_obj['data']}")

        async with aiohttp.ClientSession() as session:
            print(f"Fetching channel info for '{temp_channel_slug}' to get chatroom_id...")
            info = await get_channel_info(session, temp_channel_slug)
            
            if info and info.get("chatroom_id") and not info.get("error"):
                chatroom_id_to_test = info["chatroom_id"]
                print(f"Got chatroom_id: {chatroom_id_to_test}. Connecting to chat...")
                await listen_to_kick_chat(int(chatroom_id_to_test), simple_test_callback)
            elif info and info.get("error"):
                print(f"API Error preventing chat test: {info['error']}")
            else:
                print(f"Could not get chatroom_id for '{temp_channel_slug}'. Cannot connect to chat.")
    asyncio.run(main_test_chat())