# Kick.com Multi-Chatter

A Python-based desktop application for viewing multiple Kick.com stream chats and information simultaneously, inspired by multi-chat clients like Chatterino.

## Features

*   **Multi-Channel Viewing:** Connect to and view multiple Kick.com stream chats in a tabbed interface.
*   **Stream Information Dashboard:** Displays for each connected channel:
    *   Stream Title
    *   Current Viewer Count
    *   Stream Category
    *   Live/Offline Status
*   **Emote Display:** Renders Kick emotes directly in the chat.
*   **User-Specific Colors:** Displays usernames in their designated Kick chat colors.
*   **Badge Display:** Shows user badges (e.g., Subscriber, Moderator, VIP) next to usernames. *(Requires Cairo C library for graphical badges, otherwise shows text fallback)*
*   **Individual Channel Closing:** Close specific channel tabs without affecting others.
*   **Pin on Top:** Option to keep the application window always on top of other applications.
*   **Dark Mode UI:** Built with CustomTkinter for a modern look and feel.

## Prerequisites

*   Python 3.10+ (developed with Python 3.11/3.12 in mind for asyncio features)
*   Pip (Python package installer)

## Installation

1.  **Clone the repository (or download the source code):**
    ```bash
    git clone <your-repository-url>
    cd kick-multi-chatter 
    ```

2.  **Create and activate a virtual environment (recommended):**
    *   On Windows:
        ```bash
        python -m venv venv
        .\venv\Scripts\activate
        ```
    *   On macOS/Linux:
        ```bash
        python3 -m venv venv
        source venv/bin/activate
        ```

3.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```
    *(Alternatively, if no `requirements.txt` is provided yet, install manually):*
    ```bash
    pip install customtkinter aiohttp websockets Pillow cairosvg
    ```

4.  **(Windows Only) Install Cairo C Library for Graphical Badges:**
    `cairosvg` (used for rendering SVG badges as PNGs) requires the Cairo C library. If it's not found, badges will display as text (e.g., "[Mod]").
    *   Download and install MSYS2 from [https://www.msys2.org/](https://www.msys2.org/).
    *   Open an MSYS2 MinGW 64-bit terminal (or 32-bit if using 32-bit Python).
    *   Install Cairo:
        ```bash
        pacman -S mingw-w64-x86_64-cairo 
        # or for 32-bit: pacman -S mingw-w64-i680-cairo
        ```
    *   Add the MSYS2 MinGW bin directory (e.g., `C:\msys64\mingw64\bin`) to your system's PATH environment variable.
    *   **Restart your terminal/IDE** after updating the PATH.

## Usage

1.  Ensure your virtual environment is activated.
2.  Run the main application file:
    ```bash
    python main.py
    ```
3.  In the input field at the top, enter one or more Kick.com channel slugs (usernames), separated by commas (e.g., `xqc, adinross, SursaiKosecksi`).
4.  Click "Connect" or press Enter.
5.  Each channel will open in its own tab, displaying stream information and live chat.
6.  Use the "Pin on Top" checkbox to keep the application window above others.
7.  Click the "✕" button on a channel's info bar to close that specific channel tab.


## How It Works

*   **GUI:** Built using [CustomTkinter](https://github.com/TomSchimansky/CustomTkinter), a modern theming extension for Python's built-in Tkinter library.
*   **Async Operations:** Uses `asyncio` for non-blocking network operations (fetching stream info, connecting to chat, loading images).
*   **HTTP API:** `aiohttp` is used to make asynchronous requests to the Kick.com API V2 for stream details and user information.
*   **Chat Connection:** `websockets` library is used to connect to Kick's Pusher-based WebSocket service for live chat messages.
*   **Image Handling:** `Pillow (PIL)` is used for processing and displaying emotes and badges. `cairosvg` is used (if available) to convert SVG badges to PNGs.

## Future Enhancements / To-Do

*   [ ] More detailed error popups for users.
*   [ ] Persistent settings (e.g., last opened channels, window size/position, "pin on top" state).
*   [ ] Option to customize fonts and theme colors further.
*   [ ] Display user roles/badges more distinctively (e.g., specific icons if Kick API changes to provide them directly).
*   [ ] Clickable links in chat.
*   [ ] User muting/ignore list.
*   [ ] Chat message input field (for sending messages - requires OAuth).
*   [ ] Better handling for streams going live/offline while connected.

## Contributing

Contributions, issues, and feature requests are welcome! Please feel free to fork the repository, make changes, and submit a pull request. If you encounter any bugs or have ideas for new features, please open an issue.

## License

*(Choose a license if you wish, e.g., MIT License. If not, you can state "This project is unlicensed" or remove this section.)*

This project is licensed under the MIT License - see the `LICENSE.md` file for details (if you add one).
# kickerino
