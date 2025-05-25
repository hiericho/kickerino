# kick_api.py
import aiohttp
import asyncio
from aiohttp.client_exceptions import ContentTypeError
import traceback

API_BASE_URL = "https://kick.com/api/v2"

async def get_channel_info(session: aiohttp.ClientSession, channel_slug: str):
    url = f"{API_BASE_URL}/channels/{channel_slug}"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'application/json, text/plain, */*',
        'Accept-Language': 'en-US,en;q=0.9',
        'Referer': f'https://kick.com/{channel_slug}',
        'Origin': 'https://kick.com'
    }
    
    response_obj = None 
    try:
        async with session.get(url, headers=headers) as resp:
            response_obj = resp 
            
            content_type_header = response_obj.headers.get('Content-Type', '').lower()
            is_expected_json_type = 'application/json' in content_type_header

            if not is_expected_json_type:
                print(f"INFO: API for '{channel_slug}' returned Content-Type '{content_type_header}' (Status: {response_obj.status}), but attempting to parse as JSON.")

            response_obj.raise_for_status()
            data = await response_obj.json(content_type=None) 
            
            livestream_data = data.get("livestream")
            chatroom_data = data.get("chatroom")
            user_data = data.get("user", {})

            if not livestream_data:
                return {
                    "username": user_data.get("username", channel_slug),
                    "title": "Offline",
                    "viewers": 0,
                    "category": "N/A",
                    "chatroom_id": chatroom_data.get("id") if chatroom_data else None,
                    "is_live": False
                }

            return {
                "username": user_data.get("username", channel_slug),
                "title": livestream_data.get("session_title", "N/A"),
                "viewers": livestream_data.get("viewer_count", 0),
                "category": livestream_data.get("categories", [{}])[0].get("name", "N/A") 
                            if livestream_data.get("categories") else "N/A",
                "chatroom_id": chatroom_data.get("id") if chatroom_data else None,
                "is_live": True
            }
    
    except ContentTypeError as e:
        error_text_content = "Could not read text from erroring response (ContentTypeError)"
        current_status = "N/A"
        if response_obj:
            current_status = response_obj.status
            try:
                error_text_content = await response_obj.text()
                print(f"ContentTypeError for {channel_slug}: {e}. Status: {current_status}. Content-Type was '{response_obj.headers.get('Content-Type', '')}'.")
                print(f"Response body that caused ContentTypeError (first 300 chars): {error_text_content[:300]}")
            except Exception as read_err:
                error_text_content = f"Could not read text from erroring response: {read_err}"
        
        return {
            "error": f"JSON Parsing Failed (ContentTypeError): {e}. Server might have sent HTML or malformed JSON.",
            "status": current_status,
            "preview": error_text_content[:200].replace('\n', ' ')
        }

    except aiohttp.ClientResponseError as e:
        current_status = e.status
        print(f"API HTTP Error for {channel_slug}: {current_status} - {e.message}.")
        if current_status == 404:
            return {"error": f"Channel '{channel_slug}' not found (404).", "status": 404}
        return {"error": f"API HTTP Error: {current_status} - {e.message}", "status": current_status}

    except aiohttp.ClientConnectionError as e:
        error_message = str(e) 
        print(f"Client Connection Error fetching channel info for {channel_slug}: {error_message}")
        return {"error": f"Connection Error: {error_message}"}
        
    except Exception as e:
        print(f"An unexpected error occurred fetching channel info for {channel_slug}: {e}")
        traceback.print_exc()
        current_status = response_obj.status if response_obj else "N/A"
        return {"error": f"Unexpected error during API call: {e}", "status": current_status}

if __name__ == "__main__":
    async def main_test_api():
        async with aiohttp.ClientSession() as session:
            channel_name = "xqc" 
            print(f"Fetching info for: {channel_name}")
            info = await get_channel_info(session, channel_name)
            
            if info and not info.get("error"):
                print(f"Streamer: {info['username']}")
                print(f"Title: {info['title']}")
                print(f"Viewers: {info['viewers']}")
                print(f"Category: {info['category']}")
                print(f"Chatroom ID: {info['chatroom_id']}")
                print(f"Is Live: {info['is_live']}")
            elif info and info.get("error"):
                print(f"Error: {info['error']}")
                if info.get("preview"):
                    print(f"Preview of received data: {info['preview']}")
                if info.get("status"):
                    print(f"Status Code: {info.get('status')}")
            else:
                print(f"Could not fetch info for {channel_name} (No data or error returned).")
    asyncio.run(main_test_api())