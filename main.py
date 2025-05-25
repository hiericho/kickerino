# main.py
import customtkinter as ctk
from PIL import Image, ImageTk, UnidentifiedImageError
import asyncio
import threading
import io
import aiohttp
import traceback

# Import local modules
from kick_api import get_channel_info
from kick_chat import listen_to_kick_chat
from channel_tab import ChannelTab 
from badge_manager import BadgeManager
from emote_manager import EmoteManager # Import the new EmoteManager

# --- Global Configuration & State ---
GUI_UPDATE_QUEUE = asyncio.Queue()

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

class KickChatterApp(ctk.CTk):
    def __init__(self, loop: asyncio.AbstractEventLoop):
        super().__init__()
        self.loop = loop
        self.aiohttp_session = None 
        
        self.active_channels = {}
        # Emote cache and locks are now managed by EmoteManager
        # Badge cache and locks are managed by BadgeManager
        
        self.badge_manager = None 
        self.emote_manager = None # Will be initialized after session

        self.APP_FONT_FAMILY = "Segoe UI" 
        self.DEFAULT_FONT_SIZE = 13
        self.DEFAULT_FONT = (self.APP_FONT_FAMILY, self.DEFAULT_FONT_SIZE)
        self.TITLE_FONT = (self.APP_FONT_FAMILY, 15, "bold")
        self.INFO_FONT = (self.APP_FONT_FAMILY, 12)

        # ... (rest of __init__ as before: title, geometry, grid, input_frame, tab_view setup) ...
        self.title("Kick.com Multi-Chatter")
        self.geometry("900x750")
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)
        self.input_frame = ctk.CTkFrame(self, corner_radius=0)
        self.input_frame.grid(row=0, column=0, padx=0, pady=0, sticky="ew")
        self.input_frame.grid_columnconfigure(1, weight=1)
        self.channel_label = ctk.CTkLabel(self.input_frame, text="Channel Slug(s):", font=self.DEFAULT_FONT)
        self.channel_label.grid(row=0, column=0, padx=(10,5), pady=10)
        self.channel_entry = ctk.CTkEntry(self.input_frame, placeholder_text="e.g., xqc, adinross (comma-separated)", font=self.DEFAULT_FONT)
        self.channel_entry.grid(row=0, column=1, padx=5, pady=10, sticky="ew")
        self.channel_entry.bind("<Return>", self.connect_button_action)
        self.connect_button = ctk.CTkButton(self.input_frame, text="Connect", command=self.connect_button_action, font=self.DEFAULT_FONT)
        self.connect_button.grid(row=0, column=2, padx=(5,10), pady=10)
        self.tab_view = ctk.CTkTabview(self, corner_radius=10)
        self.tab_view.grid(row=1, column=0, padx=10, pady=(5,10), sticky="nsew")
        self._initialize_info_tab()
        self.protocol("WM_DELETE_WINDOW", self.on_closing)
        self.process_gui_updates()


    async def _ensure_session(self):
        if not self.aiohttp_session or self.aiohttp_session.closed:
            self.aiohttp_session = aiohttp.ClientSession()
            print("aiohttp session initialized.")
        
        # Initialize Managers if they haven't been, now that session is ready
        if not self.badge_manager and self.aiohttp_session:
            self.badge_manager = BadgeManager(self.loop, self.aiohttp_session)
            print("BadgeManager initialized.")
        if not self.emote_manager and self.aiohttp_session:
            self.emote_manager = EmoteManager(self.loop, self.aiohttp_session)
            print("EmoteManager initialized.")


    def _initialize_info_tab(self):
        try:
            if "Info" not in self.tab_view._name_list:
                self.tab_view.add("Info")
            tab_info_frame = self.tab_view.tab("Info") 
            if tab_info_frame: 
                for widget in tab_info_frame.winfo_children():
                    widget.destroy()
                tab_info_frame.grid_columnconfigure(0, weight=1)
                info_label = ctk.CTkLabel(tab_info_frame, 
                                          text="Enter channel slugs above (comma-separated) and click Connect.", 
                                          font=(self.APP_FONT_FAMILY, 16))
                info_label.grid(row=0, column=0, padx=20, pady=20, sticky="ew")
        except Exception as e:
            print(f"Could not initialize Info tab: {e}")

    async def _close_session(self):
        if self.aiohttp_session and not self.aiohttp_session.closed:
            await self.aiohttp_session.close()
            self.aiohttp_session = None 
            print("aiohttp session closed.")

    def connect_button_action(self, event=None):
        channel_slugs_raw = self.channel_entry.get().strip()
        if not channel_slugs_raw:
            print("[SYSTEM] Please enter channel slugs.")
            return
        channel_slugs = [slug.strip().lower() for slug in channel_slugs_raw.split(',') if slug.strip()]
        self.connect_button.configure(state="disabled", text="Connecting...")
        info_tab_exists = "Info" in self.tab_view._name_list
        if info_tab_exists and channel_slugs:
            try:
                current_tab_name = self.tab_view.get() 
                if len(self.tab_view._name_list) == 1 or (current_tab_name == "Info"):
                    self.tab_view.delete("Info")
            except Exception as e: 
                if len(self.tab_view._name_list) == 0 and info_tab_exists: 
                     pass 
                else:
                    print(f"Note: Could not delete Info tab: {e}")
        for slug in channel_slugs:
            if slug in self.active_channels:
                print(f"[SYSTEM] Already connected or connecting to {slug}.")
                if slug in self.tab_view._name_list: 
                    self.tab_view.set(slug)
                continue
            try:
                if slug not in self.tab_view._name_list:
                    self.tab_view.add(slug)
                self.tab_view.set(slug) 
            except Exception as e:
                print(f"Error adding or setting tab for {slug}: {e}")
                continue
            current_tab_frame = self.tab_view.tab(slug)
            if not current_tab_frame:
                print(f"Failed to get tab frame for {slug}. Skipping.")
                if slug in self.tab_view._name_list: 
                    try: self.tab_view.delete(slug)
                    except: pass
                if slug in self.active_channels:
                    del self.active_channels[slug]
                continue
            for widget in current_tab_frame.winfo_children():
                widget.destroy()
            channel_tab_ui = ChannelTab(current_tab_frame, slug, self)
            channel_tab_ui.pack(expand=True, fill="both")
            self.active_channels[slug] = {
                "tab_ref": channel_tab_ui, "info_task": None,
                "chat_task": None, "chatroom_id": None
            }
            channel_tab_ui.add_message_to_gui(f"[SYSTEM] Connecting to {slug}...\n", is_system=True)
            asyncio.run_coroutine_threadsafe(self._async_connect_channel(slug), self.loop)
        self.channel_entry.delete(0, "end")
        
        self.loop.call_soon_threadsafe(lambda: self.connect_button.configure(state="normal", text="Connect"))

    async def _async_connect_channel(self, channel_slug: str):
        try:
            await self._ensure_session() 
            if channel_slug not in self.active_channels: return
            chan_data = self.active_channels[channel_slug]
            if chan_data.get("info_task") and not chan_data["info_task"].done(): chan_data["info_task"].cancel()
            if chan_data.get("chat_task") and not chan_data["chat_task"].done(): chan_data["chat_task"].cancel()
            assert self.aiohttp_session is not None, "aiohttp_session must not be None"
            info = await get_channel_info(self.aiohttp_session, channel_slug)
            if channel_slug not in self.active_channels: return
            if info.get("error"):
                await GUI_UPDATE_QUEUE.put(("stream_info_error", {"slug": channel_slug, "error": info["error"]}))
                return
            self.active_channels[channel_slug]["chatroom_id"] = info.get("chatroom_id")
            await GUI_UPDATE_QUEUE.put(("stream_info_update", {"slug": channel_slug, "data": info}))
            if not info.get("is_live"):
                 await GUI_UPDATE_QUEUE.put(("system_message", {"slug": channel_slug, "message": f"Channel {info.get('username', channel_slug)} is offline."}))
            if self.active_channels[channel_slug]["chatroom_id"]:
                chatroom_id = self.active_channels[channel_slug]["chatroom_id"]
                await GUI_UPDATE_QUEUE.put(("system_message", {"slug": channel_slug, "message": f"Joining chat for {info.get('username', channel_slug)}..."}))
                async def on_chat_event(event_data_obj):
                    await GUI_UPDATE_QUEUE.put(("chat_event", {"slug": channel_slug, "event": event_data_obj}))
                chat_task = self.loop.create_task(listen_to_kick_chat(chatroom_id, on_chat_event))
                self.active_channels[channel_slug]["chat_task"] = chat_task
            else:
                await GUI_UPDATE_QUEUE.put(("system_message", {"slug": channel_slug, "message": f"Could not find chatroom for {channel_slug}."}))
        except asyncio.CancelledError:
            if channel_slug in self.active_channels: 
                await GUI_UPDATE_QUEUE.put(("system_message", {"slug": channel_slug, "message": f"Connection to {channel_slug} cancelled."}))
        except Exception as e:
            print(f"Error in _async_connect_channel for {channel_slug}: {e}")
            traceback.print_exc()
            if channel_slug in self.active_channels: 
                await GUI_UPDATE_QUEUE.put(("system_message", {"slug": channel_slug, "message": f"Connection to {channel_slug} failed: {type(e).__name__} - {e}"}))

    def close_specific_channel(self, channel_slug: str):
        print(f"Main app: Closing channel {channel_slug}")
        if channel_slug in self.active_channels:
            channel_data = self.active_channels[channel_slug]
            tasks_to_await_for_close = []
            if channel_data.get("info_task") and not channel_data["info_task"].done(): channel_data["info_task"].cancel()
            if channel_data.get("chat_task") and not channel_data["chat_task"].done():
                channel_data["chat_task"].cancel()
                tasks_to_await_for_close.append(channel_data["chat_task"])
            if tasks_to_await_for_close and self.loop.is_running():
                async def await_channel_close_tasks():
                    print(f"Awaiting cancellation of tasks for {channel_slug}...")
                    await asyncio.gather(*tasks_to_await_for_close, return_exceptions=True)
                    print(f"Tasks for {channel_slug} finalized.")
                asyncio.run_coroutine_threadsafe(await_channel_close_tasks(), self.loop)
            if channel_slug in self.tab_view._name_list:
                try:
                    current_active_tab = self.tab_view.get()
                    self.tab_view.delete(channel_slug)
                    print(f"Tab for {channel_slug} deleted.")
                    if current_active_tab == channel_slug and len(self.tab_view._name_list) > 0:
                        self.tab_view.set(self.tab_view._name_list[0]) 
                except Exception as e: print(f"Error deleting or resetting tab for {channel_slug}: {e}")
            del self.active_channels[channel_slug]
            print(f"Channel {channel_slug} removed from active channels.")
            if not self.active_channels and "Info" not in self.tab_view._name_list:
                self._initialize_info_tab()
                if "Info" in self.tab_view._name_list: 
                    self.tab_view.set("Info")
        else: print(f"Attempted to close non-active channel: {channel_slug}")

    def process_gui_updates(self):
        try:
            while not GUI_UPDATE_QUEUE.empty():
                task_type, payload = GUI_UPDATE_QUEUE.get_nowait()
                channel_slug = payload.get("slug")
                if task_type not in ["emote_image_loaded", "badge_image_loaded"] and \
                   (not channel_slug or channel_slug not in self.active_channels):
                    GUI_UPDATE_QUEUE.task_done()
                    continue
                tab_ui = self.active_channels.get(channel_slug, {}).get("tab_ref") if channel_slug else None
                if not tab_ui and task_type not in ["emote_image_loaded", "badge_image_loaded"]:
                    GUI_UPDATE_QUEUE.task_done()
                    continue

                if task_type == "stream_info_update":
                    if tab_ui:
                        tab_ui.update_stream_info(payload["data"])
                elif task_type == "stream_info_error":
                    if tab_ui:
                        tab_ui.update_stream_info_error(payload["error"])
                elif task_type == "chat_event":
                    event_detail = payload["event"]
                    if tab_ui:
                        if event_detail["type"] == "chat":
                            tab_ui.display_chat_message(event_detail["data"])
                        elif event_detail["type"] == "system":
                            tab_ui.add_message_to_gui(f"[SYSTEM] {event_detail['data']}\n", is_system=True)
                        elif event_detail["type"] == "error":
                            tab_ui.add_message_to_gui(f"[ERROR] Chat: {event_detail['data']}\n", is_error=True)
                elif task_type == "system_message":
                    if tab_ui:
                        tab_ui.add_message_to_gui(f"{payload['message']}\n", is_system=True)
                elif task_type == "emote_image_loaded":
                    pass # Handled by ChannelTab re-checking cache
                elif task_type == "badge_image_loaded":
                    pass # Handled by ChannelTab re-checking cache
                GUI_UPDATE_QUEUE.task_done()
        except asyncio.QueueEmpty: pass 
        except Exception as e:
            print(f"Error in process_gui_updates: {e}")
            traceback.print_exc()
        finally: self.after(100, self.process_gui_updates)
            
    def on_closing(self):
        print("Closing application - Initiating task cancellation...")
        tasks_to_await = []
        for slug, data in list(self.active_channels.items()):
            if data.get("info_task") and not data["info_task"].done(): data["info_task"].cancel()
            if data.get("chat_task") and not data["chat_task"].done():
                data["chat_task"].cancel()
                tasks_to_await.append(data["chat_task"])
        if self.loop.is_running():
            if self.aiohttp_session and not self.aiohttp_session.closed:
                session_close_task = self.loop.create_task(self._close_session())
                tasks_to_await.append(session_close_task)
            if tasks_to_await:
                async def await_app_shutdown_tasks():
                    print(f"Awaiting {len(tasks_to_await)} app-level tasks during shutdown...")
                    await asyncio.gather(*tasks_to_await, return_exceptions=True)
                    print("App-level tasks finalized in on_closing.")
                asyncio.run_coroutine_threadsafe(await_app_shutdown_tasks(), self.loop)
        self.destroy()
        print("Tkinter window destroyed.")


# ... (run_async_loop and if __name__ == "__main__": block remain the same as before) ...
def run_async_loop(loop: asyncio.AbstractEventLoop):
    asyncio.set_event_loop(loop)
    try: loop.run_forever()
    except KeyboardInterrupt: print("Asyncio loop interrupted by KeyboardInterrupt.")
    finally:
        print("Asyncio loop stopping procedure initiated...")
        pending_tasks = [task for task in asyncio.all_tasks(loop=loop) if not task.done()]
        if pending_tasks:
            print(f"Cancelling {len(pending_tasks)} remaining pending tasks in run_async_loop...")
            for task in pending_tasks: task.cancel()
            async def finalize_tasks_in_loop():
                print("Awaiting finalization of cancelled tasks in run_async_loop...")
                await asyncio.gather(*pending_tasks, return_exceptions=True)
                print("All pending tasks finalized in run_async_loop.")
            if loop.is_running(): loop.run_until_complete(finalize_tasks_in_loop())
            else: print("Loop was not running to finalize tasks in run_async_loop.")
        print("Asyncio loop has stopped.")

if __name__ == "__main__":
    async_event_loop = asyncio.new_event_loop()
    # async_event_loop.set_debug(True)
    loop_thread = threading.Thread(target=run_async_loop, args=(async_event_loop,), daemon=True)
    loop_thread.start()
    app = KickChatterApp(loop=async_event_loop)
    app.mainloop()
    print("Tkinter mainloop finished. Signaling asyncio loop to stop.")
    if async_event_loop.is_running(): async_event_loop.call_soon_threadsafe(async_event_loop.stop)
    print("Waiting for asyncio loop thread to join...")
    loop_thread.join(timeout=10) 
    if loop_thread.is_alive(): print("Warning: Asyncio loop thread did not finish in the allotted time.")
    else: print("Asyncio loop thread has joined.")
    if not async_event_loop.is_closed():
        print("Closing asyncio event loop...")
        try:
            all_remaining_tasks = asyncio.all_tasks(async_event_loop)
            if all_remaining_tasks:
                print(f"Final cleanup: Awaiting {len(all_remaining_tasks)} tasks before loop close...")
                if async_event_loop.is_running():
                    async_event_loop.run_until_complete(asyncio.gather(*all_remaining_tasks, return_exceptions=True))
                else: 
                    for task in all_remaining_tasks: task.cancel()
        except RuntimeError as e: print(f"RuntimeError during final task gathering: {e}. Loop might be already closed.")
        except Exception as e: print(f"Unexpected error during final task gathering: {e}")
        async_event_loop.close()
        print("Asyncio event loop closed.")
    else: print("Asyncio event loop was already closed.")
    print("Application finished.")