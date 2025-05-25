# channel_tab.py
import customtkinter as ctk
import asyncio
import re

DEFAULT_USERNAME_COLOR = "#6495ED"

class ChatLine(ctk.CTkFrame):
    def __init__(self, master, app_instance):
        super().__init__(master, fg_color="transparent")
        self.app = app_instance
        self.image_references = [] 
    def add_text(self, text_content, text_color=None, font=None):
        if not font: font = self.app.DEFAULT_FONT
        label = ctk.CTkLabel(self, text=text_content, text_color=text_color, font=font, anchor="w")
        label.pack(side="left", pady=0, padx=0)
    def add_image(self, tk_image):
        if tk_image:
            self.image_references.append(tk_image) 
            label = ctk.CTkLabel(self, image=tk_image, text="", anchor="w")
            label.pack(side="left", pady=(0, 2), padx=1)

class ChannelTab(ctk.CTkFrame):
    def __init__(self, master, channel_slug: str, app_instance):
        super().__init__(master, fg_color="transparent")
        self.channel_slug = channel_slug
        self.app = app_instance 
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1) 
        self.top_controls_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.top_controls_frame.grid(row=0, column=0, padx=5, pady=(5,0), sticky="ew")
        self.top_controls_frame.grid_columnconfigure(0, weight=1)
        self.info_frame = ctk.CTkFrame(self.top_controls_frame, corner_radius=10)
        self.info_frame.grid(row=0, column=0, sticky="ew")
        self.info_frame.grid_columnconfigure(0, weight=1)
        self.stream_title_label = ctk.CTkLabel(self.info_frame, text=f"Title ({channel_slug}): N/A", anchor="w", wraplength=650, font=self.app.TITLE_FONT) 
        self.stream_title_label.grid(row=0, column=0, columnspan=2, padx=10, pady=(5,2), sticky="w")
        self.details_frame = ctk.CTkFrame(self.info_frame, fg_color="transparent")
        self.details_frame.grid(row=1, column=0, padx=10, pady=(0,5), sticky="ew")
        self.viewers_label = ctk.CTkLabel(self.details_frame, text="Viewers: N/A", anchor="w", font=self.app.INFO_FONT)
        self.viewers_label.pack(side="left", padx=(0,15))
        self.category_label = ctk.CTkLabel(self.details_frame, text="Category: N/A", anchor="w", font=self.app.INFO_FONT)
        self.category_label.pack(side="left")
        self.live_status_label = ctk.CTkLabel(self.details_frame, text="CONNECTING...", anchor="e", font=self.app.INFO_FONT, text_color="orange")
        self.live_status_label.pack(side="right", padx=(0,5))
        self.close_button = ctk.CTkButton(
            self.top_controls_frame, text="✕", width=30, height=30,
            font=(self.app.APP_FONT_FAMILY, 16, "bold"),
            fg_color="#FF6347", hover_color="#E55337", command=self.request_close_channel)
        self.close_button.grid(row=0, column=1, padx=(5,0), pady=(0,0), sticky="ne")
        self.chat_scroll_frame = ctk.CTkScrollableFrame(self, corner_radius=10, fg_color="transparent")
        self.chat_scroll_frame.grid(row=1, column=0, padx=5, pady=5, sticky="nsew")
        self.chat_lines_container = [] 

    def request_close_channel(self): self.app.close_specific_channel(self.channel_slug)
    def update_stream_info(self, info_data: dict):
        self.stream_title_label.configure(text=f"{info_data['title']}")
        self.viewers_label.configure(text=f"Viewers: {info_data['viewers']:,}")
        self.category_label.configure(text=f"Category: {info_data['category']}")
        self.live_status_label.configure(text="LIVE" if info_data.get('is_live') else "OFFLINE", 
                                         text_color="#77dd77" if info_data.get('is_live') else "#ff6961")
    def update_stream_info_error(self, error_message: str):
        self.stream_title_label.configure(text="Title: Error"); self.viewers_label.configure(text="Viewers: N/A")
        self.category_label.configure(text="Category: N/A"); self.live_status_label.configure(text="ERROR", text_color="orange")
        self.add_message_to_gui(f"[ERROR] API: {error_message}\n", is_error=True)
    def add_message_to_gui(self, text_content, is_system=True, is_error=False):
        line_frame = ChatLine(self.chat_scroll_frame, self.app)
        line_frame.pack(side="top", fill="x", anchor="w", pady=(0,2))
        color = "gray" if is_system else ("#ff6961" if is_error else None)
        line_frame.add_text(text_content.strip(), text_color=color, font=self.app.DEFAULT_FONT)
        self.chat_lines_container.append(line_frame); self._scroll_to_bottom()
    
    def _parse_message_content(self, content_with_kick_placeholders: str, kick_emotes_meta: list, channel_slug_for_7tv: str):
        final_parts = []
        kick_pattern = re.compile(r"\[emote:(\d+):([^\]]+)\]")
        kick_emote_data_map = {str(e.get("id", "")): e for e in kick_emotes_meta if e.get("id")}
        last_idx_kick = 0
        intermediate_segments = []
        for kick_match in kick_pattern.finditer(content_with_kick_placeholders):
            emote_id_in_placeholder = kick_match.group(1)
            start, end = kick_match.span()
            if start > last_idx_kick: intermediate_segments.append(("text", content_with_kick_placeholders[last_idx_kick:start]))
            kick_emote_obj = kick_emote_data_map.get(emote_id_in_placeholder)
            intermediate_segments.append(("kick_emote", kick_emote_obj) if kick_emote_obj else ("text", kick_match.group(0)))
            last_idx_kick = end
        if last_idx_kick < len(content_with_kick_placeholders): intermediate_segments.append(("text", content_with_kick_placeholders[last_idx_kick:]))

        if not self.app.emote_manager: return intermediate_segments
        for part_type, part_data in intermediate_segments:
            if part_type == "text":
                text_segment = part_data; current_pos_in_segment = 0
                words = re.split(r'(\s+)', text_segment) # Split by spaces, keeping spaces
                for word_or_space in words:
                    if not word_or_space.strip(): # If it's only whitespace
                        final_parts.append(("text", word_or_space))
                        continue
                    seventv_emote_data = self.app.emote_manager.get_7tv_emote_data(word_or_space, channel_slug_for_7tv)
                    if seventv_emote_data: final_parts.append(("7tv_emote", seventv_emote_data))
                    else: final_parts.append(("text", word_or_space))
            else: final_parts.append((part_type, part_data))
        
        consolidated_parts = []; current_text = ""
        for p_type, p_data in final_parts:
            if p_type == "text": current_text += p_data
            else:
                if current_text: consolidated_parts.append(("text", current_text)); current_text = ""
                consolidated_parts.append((p_type, p_data))
        if current_text: consolidated_parts.append(("text", current_text))
        return consolidated_parts

    def _scroll_to_bottom(self):
        self.chat_scroll_frame._parent_canvas.after(30, lambda: self.chat_scroll_frame._parent_canvas.yview_moveto(1.0))

    def display_chat_message(self, message_data: dict):
        line_frame = ChatLine(self.chat_scroll_frame, self.app)
        line_frame.pack(side="top", fill="x", anchor="w", pady=(0,2)) 
        self.chat_lines_container.append(line_frame)
        sender_info = message_data.get("sender", {}); sender_name = sender_info.get("username", "Anon")
        identity = sender_info.get("identity", {}); user_color = identity.get("color", DEFAULT_USERNAME_COLOR) 
        user_badges = identity.get("badges", [])

        if self.app.badge_manager: 
            for badge_data in user_badges:
                if badge_data.get("active") is False: continue
                badge_type = badge_data.get("type"); badge_text_fallback = f"[{badge_data.get('text', badge_type or 'badge')}]"
                badge_svg_url = self.app.badge_manager.get_badge_svg_url(badge_type)
                if badge_svg_url:
                    tk_badge_image = self.app.badge_manager.get_cached_badge_image(badge_svg_url)
                    if tk_badge_image: line_frame.add_image(tk_badge_image)
                    elif tk_badge_image is None and badge_svg_url in self.app.badge_manager.badge_image_cache: 
                        line_frame.add_text(badge_text_fallback + " ", font=self.app.INFO_FONT)
                    else: 
                        line_frame.add_text(badge_text_fallback + " ", font=self.app.INFO_FONT)
                        asyncio.run_coroutine_threadsafe(
                            self.app.badge_manager.load_and_cache_badge_svg(badge_svg_url, badge_type or "unknown"), self.app.loop)
                else: line_frame.add_text(badge_text_fallback + " ", font=self.app.INFO_FONT)
        
        line_frame.add_text(f"{sender_name}", text_color=user_color, font=(self.app.APP_FONT_FAMILY, self.app.DEFAULT_FONT_SIZE, "bold"))
        line_frame.add_text(": ", text_color=user_color if user_color != DEFAULT_USERNAME_COLOR else None)
        
        content_with_kick_placeholders = message_data.get("content", "")
        kick_emotes_meta_array = message_data.get("emotes", [])
        message_parts = self._parse_message_content(content_with_kick_placeholders, kick_emotes_meta_array, self.channel_slug)

        if self.app.emote_manager:
            for part_type, part_data in message_parts:
                if part_type == "text": line_frame.add_text(part_data)
                elif part_type == "kick_emote": 
                    name, url = part_data.get('name', 'emote'), part_data.get('url')
                    if not url: line_frame.add_text(f"[{name}]"); continue
                    img = self.app.emote_manager.get_cached_kick_emote_image(url)
                    if img: line_frame.add_image(img)
                    elif img is None and url in self.app.emote_manager.kick_emote_cache: line_frame.add_text(f"[{name}]")
                    else: 
                        line_frame.add_text(f"[{name}]") 
                        asyncio.run_coroutine_threadsafe(self.app.emote_manager.load_and_cache_kick_emote(url, name), self.app.loop)
                elif part_type == "7tv_emote":
                    name, url = part_data.get('name', '7tv_emote'), part_data.get('url')
                    if not url: line_frame.add_text(f"[{name}]"); continue
                    img = self.app.emote_manager.get_cached_7tv_emote_image(url)
                    if img: line_frame.add_image(img)
                    elif img is None and url in self.app.emote_manager.seventv_emote_cache: line_frame.add_text(f"[{name}]")
                    else:
                        line_frame.add_text(f"[{name}]")
                        asyncio.run_coroutine_threadsafe(self.app.emote_manager.load_and_cache_7tv_emote(part_data), self.app.loop)
        else: line_frame.add_text(content_with_kick_placeholders)
        self._scroll_to_bottom()