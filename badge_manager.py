# badge_manager.py
import asyncio
import aiohttp
from PIL import Image, ImageTk, UnidentifiedImageError
import io
import traceback

try:
    import cairosvg
    CAIROSVG_AVAILABLE = True
    # print("BadgeManager: cairosvg library successfully imported.")
except ImportError as e:
    CAIROSVG_AVAILABLE = False
    print(f"BadgeManager: cairosvg library import FAILED: {e}. Badges will be text.")
    if "no library called" in str(e) or "cannot load library" in str(e):
        print("This OSError often means the Cairo C library is missing or not in your system PATH.")

BADGE_SIZE = (18, 18) 
PREDEFINED_BADGE_SVGS = {
    "moderator": "https://www.kickdatabase.com/kickBadges/moderator.svg",
    "subscriber": "https://www.kickdatabase.com/kickBadges/subscriber.svg",
    "founder": "https://www.kickdatabase.com/kickBadges/founder.svg",
    "vip": "https://www.kickdatabase.com/kickBadges/vip.svg",
    "og": "https://www.kickdatabase.com/kickBadges/og.svg",
    "staff": "https://www.kickdatabase.com/kickBadges/staff.svg",
    "verified": "https://www.kickdatabase.com/kickBadges/verified.svg",
    "broadcaster": "https://www.kickdatabase.com/kickBadges/broadcaster.svg",
    "sub_gifter": "https://www.kickdatabase.com/kickBadges/subGifter.svg",
    "sidekick": "https://www.kickdatabase.com/kickBadges/sidekick.svg",
    "trainwreckstv": "https://www.kickdatabase.com/kickBadges/trainwreckstv.svg",
}

class BadgeManager:
    def __init__(self, loop: asyncio.AbstractEventLoop, aiohttp_session: aiohttp.ClientSession):
        self.loop = loop
        self.aiohttp_session = aiohttp_session
        self.badge_image_cache = {}
        self.badge_fetch_locks = {}
        self.cairosvg_available = CAIROSVG_AVAILABLE
        # if not self.cairosvg_available:
        #     print("BadgeManager initialized: cairosvg IS NOT available.")
        # else:
        #     print("BadgeManager initialized: cairosvg IS available.")

    def get_badge_svg_url(self, badge_type: str) -> str | None:
        return PREDEFINED_BADGE_SVGS.get(badge_type)

    def get_cached_badge_image(self, svg_url: str) -> ImageTk.PhotoImage | None:
        return self.badge_image_cache.get(svg_url)

    async def load_and_cache_badge_svg(self, svg_url: str, badge_identifier_for_log: str):
        if not self.cairosvg_available:
            if svg_url not in self.badge_image_cache:
                 self.badge_image_cache[svg_url] = None
            return
        if svg_url in self.badge_image_cache: return
        if svg_url not in self.badge_fetch_locks:
            self.badge_fetch_locks[svg_url] = asyncio.Lock()
        async with self.badge_fetch_locks[svg_url]:
            if svg_url in self.badge_image_cache: return
            tk_image = None
            svg_data_bytes = None
            try:
                if not self.aiohttp_session or self.aiohttp_session.closed:
                    # print(f"BadgeManager: aiohttp session is closed for {badge_identifier_for_log}.")
                    self.badge_image_cache[svg_url] = None; return
                async with self.aiohttp_session.get(svg_url) as response:
                    if response.status == 200:
                        svg_data_bytes = await response.read()
                        try:
                            png_data = cairosvg.svg2png(bytestring=svg_data_bytes, output_width=BADGE_SIZE[0], output_height=BADGE_SIZE[1])
                            if png_data is not None:
                                pil_image = Image.open(io.BytesIO(png_data))
                                if pil_image.mode != 'RGBA': pil_image = pil_image.convert('RGBA')
                                tk_image = ImageTk.PhotoImage(pil_image)
                            else:
                                print(f"BadgeManager: cairosvg.svg2png returned None for {badge_identifier_for_log} from {svg_url}")
                        except Exception as e_render:
                            print(f"BadgeManager: Error rendering/converting SVG for {badge_identifier_for_log} from {svg_url}: {e_render}")
                            # traceback.print_exc() # Uncomment for full trace if needed
                            # if svg_data_bytes: # Log snippet
                            #     try:
                            #         svg_text_snippet = svg_data_bytes.decode('utf-8', errors='ignore')
                            #         # print(f"--- SVG Snippet for {svg_url} ---\n{svg_text_snippet[:500]}\n--- End Snippet ---")
                            #     except: pass
                    else:
                        print(f"BadgeManager: Failed to fetch SVG {badge_identifier_for_log} from {svg_url}: HTTP {response.status}")
            except aiohttp.ClientError as e_http: print(f"BadgeManager: HTTP error fetching SVG for {badge_identifier_for_log}: {e_http}")
            except Exception as e_general: print(f"BadgeManager: General error loading badge {badge_identifier_for_log}: {e_general}") #traceback.print_exc()
            self.badge_image_cache[svg_url] = tk_image