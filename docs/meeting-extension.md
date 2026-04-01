## Meeting Extension Setup

This extension injects a TalkSync overlay into Google Meet, Microsoft Teams, and Zoho Meeting and lets you capture meeting audio or use platform captions when available.

### What it does

- Adds a TalkSync panel on supported meeting pages
- Connects to the local backend at `ws://127.0.0.1:8000/ws/realtime`
- Joins a TalkSync session as the current platform listener
- Captures tab audio through `getDisplayMedia`
- Reads on-page captions when available for faster translation
- Sends WAV audio chunks or direct caption text to the backend
- Shows captions and translated text in the overlay

### Supported pages

- `meet.google.com`
- `teams.microsoft.com`
- `meeting.zoho.com`

### Current limitations

- You must manually choose the current meeting tab and enable audio sharing when using audio mode.
- Caption mode depends on the meeting platform exposing captions in the page DOM.
- This is an overlay-based integration, not a finished Chrome Web Store extension.
- It does not inject translated audio back to other meeting participants.

### Load the extension

1. Open `chrome://extensions`
2. Enable `Developer mode`
3. Click `Load unpacked`
4. Select the [extension](c:/laragon/www/TalkSync/extension) folder

### Run the backend

```powershell
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

### Test on a supported platform

1. Join a supported meeting in Chrome.
2. Reload the page after reloading the extension.
3. Use the TalkSync overlay in the meeting page.
4. Click `Connect`
5. Click `Join`
6. For fastest results, enable platform captions and click `Use ... Captions`
7. Otherwise click `Capture ... Audio`
8. Watch the overlay for captions and translated text.
