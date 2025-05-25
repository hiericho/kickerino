# emote_manager.py
import asyncio
import aiohttp
from PIL import Image, ImageTk, UnidentifiedImageError
import io
import traceback
from typing import Optional

EMOTE_SIZE = (28, 28)
SEVENTV_API_BASE = "https://7tv.io/v3"

class EmoteManager:
    def __init__(self, loop: asyncio.AbstractEventLoop, aiohttp_session: aiohttp.ClientSession):
        self.loop = loop
        self.aiohttp_session = aiohttp_session
        self.kick_emote_cache = {} 
        self.seventv_emote_cache = {}
        self.kick_fetch_locks = {}
        self.seventv_fetch_locks = {}
        self.seventv_global_emotes_map = {}
        self.seventv_channel_emotes_map = {} 
        self.emote_size = EMOTE_SIZE

    def get_cached_kick_emote_image(self, emote_url: str) -> ImageTk.PhotoImage | None:
        return self.kick_emote_cache.get(emote_url)

    async def load_and_cache_kick_emote(self, emote_url: str, emote_name_for_log: str):
        if emote_url in self.kick_emote_cache: return
        if emote_url not in self.kick_fetch_locks:
            self.kick_fetch_locks[emote_url] = asyncio.Lock()
        async with self.kick_fetch_locks[emote_url]:
            if emote_url in self.kick_emote_cache: return
            tk_image = await self._fetch_and_process_image(emote_url, emote_name_for_log, "Kick")
            self.kick_emote_cache[emote_url] = tk_image
    def get_7tv_emote_data(self, emote_name: str, channel_slug: Optional[str] = None) -> dict | None:
        if channel_slug and channel_slug in self.seventv_channel_emotes_map:
            emote_data = self.seventv_channel_emotes_map[channel_slug].get(emote_name)
            if emote_data:
                return emote_data
        return self.seventv_global_emotes_map.get(emote_name)

    def get_cached_7tv_emote_image(self, emote_url: str) -> ImageTk.PhotoImage | None:
        return self.seventv_emote_cache.get(emote_url)

    async def load_and_cache_7tv_emote(self, emote_data: dict):
        emote_url = emote_data.get("url")
        emote_name = emote_data.get("name", "7tv_emote")
        if not emote_url:
            print(f"EmoteManager: No URL provided for 7TV emote {emote_name}")
            return
        if emote_url in self.seventv_emote_cache: return
        if emote_url not in self.seventv_fetch_locks:
            self.seventv_fetch_locks[emote_url] = asyncio.Lock()
        async with self.seventv_fetch_locks[emote_url]:
            if emote_url in self.seventv_emote_cache: return
            tk_image = await self._fetch_and_process_image(emote_url, emote_name, "7TV")
            self.seventv_emote_cache[emote_url] = tk_image

    async def fetch_7tv_global_emotes(self):
        if self.seventv_global_emotes_map:
            # print("EmoteManager: 7TV global emotes already loaded.")
            return
        
        global_emote_set_id = "62c5c40b1f72c3377d8a1074" # Example 7TV Global Emote Set ID (VERIFY THIS!)
        url = f"{SEVENTV_API_BASE}/emote-sets/{global_emote_set_id}"
        
        print(f"EmoteManager: Fetching 7TV global emotes from {url}...")
        try:
            if not self.aiohttp_session or self.aiohttp_session.closed:
                print("EmoteManager: aiohttp session not ready for 7TV global emotes.")
                return
            async with self.aiohttp_session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    emotes = data.get("emotes", [])
                    for emote in emotes:
                        name = emote.get("name")
                        emote_id = emote.get("id")
                        host_url_part = emote.get("data", {}).get("host", {}).get("url")
                        files = emote.get("data", {}).get("host", {}).get("files", [])
                        chosen_file = self._select_7tv_emote_file(files)
                        if name and host_url_part and chosen_file and chosen_file.get("name"):
                            full_host_url = host_url_part
                            if full_host_url.startswith("//"): full_host_url = "https:" + full_host_url
                            image_url = f"{full_host_url}/{chosen_file['name']}"
                            self.seventv_global_emotes_map[name] = {
                                "url": image_url, "name": name, "id": emote_id,
                                "animated": emote.get("data", {}).get("animated", False),
                                "source": "7tv_global"
                            }
                    print(f"EmoteManager: Loaded {len(self.seventv_global_emotes_map)} 7TV global emotes.")
                else:
                    print(f"EmoteManager: Failed to fetch 7TV global emotes, status: {response.status} from {url}")
        except Exception as e:
            print(f"EmoteManager: Error fetching 7TV global emotes: {e}")
            traceback.print_exc()

    def _select_7tv_emote_file(self, files: list) -> dict | None:
        """Selects preferred emote file (e.g., 1x WEBP)."""
        chosen_file = None
        # Prioritize 1x static formats first for simplicity with PhotoImage
        for f_format in ["WEBP", "PNG"]: # Static preferred
            for f_size_prefix in ["1x", "2x"]: 
                for file_info in files:
                    if file_info.get("name", "").startswith(f_size_prefix) and \
                       file_info.get("format") == f_format:
                        chosen_file = file_info
                        return chosen_file # Return as soon as preferred static is found
        # Fallback to AVIF or GIF if static WEBP/PNG not found
        for f_format in ["AVIF", "GIF"]:
            for f_size_prefix in ["1x", "2x"]:
                for file_info in files:
                    if file_info.get("name", "").startswith(f_size_prefix) and \
                       file_info.get("format") == f_format:
                        chosen_file = file_info
                        return chosen_file
        if not chosen_file and files: chosen_file = files[0] # Absolute fallback
        return chosen_file

    async def fetch_7tv_channel_emotes(self, kick_user_id: str, channel_slug_for_map: str):
        emote_set_id_to_fetch = None
        try:
            # ATTEMPT TO GET 7TV USER PROFILE BY KICK ID TO FIND THEIR EMOTE SET
            # THIS ENDPOINT IS A GUESS AND MIGHT NOT WORK OR EXIST.
            # YOU **MUST** VERIFY THE CORRECT WAY TO GET A KICK CHANNEL'S 7TV EMOTE SET ID.
            user_lookup_url = f"{SEVENTV_API_BASE}/users/kick/{kick_user_id}" 
            print(f"EmoteManager: Looking up 7TV user for Kick ID {kick_user_id} at {user_lookup_url}")
            async with self.aiohttp_session.get(user_lookup_url) as user_resp:
                if user_resp.status == 200:
                    user_data = await user_resp.json()
                    emote_set = user_data.get("emote_set") # 7TV user object often has an 'emote_set' field
                    if emote_set and emote_set.get("id"):
                        emote_set_id_to_fetch = emote_set.get("id")
                        print(f"EmoteManager: Found 7TV emote set ID {emote_set_id_to_fetch} for Kick user {kick_user_id} ({channel_slug_for_map})")
                    else:
                        print(f"EmoteManager: Kick user {kick_user_id} ({channel_slug_for_map}) found on 7TV but no active emote_set.id. Data: {str(user_data)[:200]}...")
                elif user_resp.status == 404:
                     print(f"EmoteManager: Kick user {kick_user_id} ({channel_slug_for_map}) not found on 7TV via /users/kick/ endpoint.")
                else:
                    print(f"EmoteManager: Error {user_resp.status} looking up 7TV user for Kick ID {kick_user_id} ({channel_slug_for_map}).")
        except Exception as e_user_lookup:
            print(f"EmoteManager: Exception during 7TV user lookup for Kick ID {kick_user_id} ({channel_slug_for_map}): {e_user_lookup}")
        
        if not emote_set_id_to_fetch:
            # print(f"EmoteManager: No 7TV emote set ID determined for {channel_slug_for_map}. Skipping channel-specific 7TV emotes.")
            self.seventv_channel_emotes_map[channel_slug_for_map] = {}
            return

        url = f"{SEVENTV_API_BASE}/emote-sets/{emote_set_id_to_fetch}"
        print(f"EmoteManager: Fetching 7TV channel emotes for {channel_slug_for_map} (Set ID: {emote_set_id_to_fetch}) from {url}...")
        channel_emotes = {}
        try:
            if not self.aiohttp_session or self.aiohttp_session.closed:
                print(f"EmoteManager: aiohttp session not ready for 7TV channel emotes ({channel_slug_for_map}).")
                return
            async with self.aiohttp_session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    emotes = data.get("emotes", [])
                    for emote in emotes:
                        name = emote.get("name")
                        emote_id = emote.get("id")
                        host_url_part = emote.get("data", {}).get("host", {}).get("url")
                        files = emote.get("data", {}).get("host", {}).get("files", [])
                        chosen_file = self._select_7tv_emote_file(files)
                        if name and host_url_part and chosen_file and chosen_file.get("name"):
                            full_host_url = host_url_part
                            if full_host_url.startswith("//"): full_host_url = "https:" + full_host_url
                            image_url = f"{full_host_url}/{chosen_file['name']}"
                            channel_emotes[name] = {
                                "url": image_url, "name": name, "id": emote_id,
                                "animated": emote.get("data", {}).get("animated", False),
                                "source": "7tv_channel"
                            }
                    self.seventv_channel_emotes_map[channel_slug_for_map] = channel_emotes
                    print(f"EmoteManager: Loaded {len(channel_emotes)} 7TV channel emotes for {channel_slug_for_map}.")
                else:
                    print(f"EmoteManager: Failed to fetch 7TV channel emotes for {channel_slug_for_map}, status: {response.status} (URL: {url})")
                    self.seventv_channel_emotes_map[channel_slug_for_map] = {}
        except Exception as e:
            print(f"EmoteManager: Error fetching 7TV channel emotes for {channel_slug_for_map}: {e}")
            traceback.print_exc()
            self.seventv_channel_emotes_map[channel_slug_for_map] = {}

    async def _fetch_and_process_image(self, image_url: str, name_for_log: str, source_for_log: str) -> ImageTk.PhotoImage | None:
        tk_image = None
        try:
            async with self.aiohttp_session.get(image_url) as response:
                if response.status == 200:
                    image_data = await response.read()
                    try:
                        pil_image = Image.open(io.BytesIO(image_data))
                        if pil_image.mode not in ('RGBA', 'LA') and 'transparency' not in pil_image.info:
                            pil_image = pil_image.convert('RGBA')
                        is_animated = getattr(pil_image, "is_animated", False)
                        num_frames = getattr(pil_image, 'n_frames', 1)
                        if is_animated and num_frames > 1:
                            pil_image.seek(0)
                            frame_image = pil_image.copy()
                            if frame_image.mode not in ('RGBA', 'LA') and 'transparency' not in frame_image.info:
                                 frame_image = frame_image.convert('RGBA')
                            resized_image = frame_image.resize(self.emote_size, Image.Resampling.LANCZOS)
                        else:
                            resized_image = pil_image.resize(self.emote_size, Image.Resampling.LANCZOS)
                        tk_image = ImageTk.PhotoImage(resized_image)
                    except UnidentifiedImageError: print(f"EmoteManager: Could not identify {source_for_log} image from {image_url} for {name_for_log}.")
                    except Exception as e_pil: print(f"EmoteManager: PIL/Tkinter error for {source_for_log} emote {name_for_log} from {image_url}: {e_pil}")
                else:
                    print(f"EmoteManager: Failed to fetch {source_for_log} image for {name_for_log} from {image_url}: HTTP {response.status}")
        except aiohttp.ClientError as e_http: print(f"EmoteManager: HTTP error fetching {source_for_log} image for {name_for_log}: {e_http}")
        except Exception as e_general: print(f"EmoteManager: General error loading {source_for_log} image {name_for_log}: {e_general}")
        return tk_image