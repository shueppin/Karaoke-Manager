from flask import Flask, render_template, Response
import threading
from queue import Queue
import time


class VideoServer:
    def __init__(self, host='127.0.0.1', port=5000):
        self.host = host
        self.port = port
        self.app = Flask(__name__)
        self.current_video = {"url": "https://www.youtube.com"}
        self.subscribers = []
        self._setup_routes()

    def _setup_routes(self):
        @self.app.route('/')
        def index():
            return render_template('index.html', video_url=self.current_video["url"])

        @self.app.route('/video-stream')
        def video_stream():
            def event_stream(queue):
                while True:
                    url = queue.get()
                    yield f"data: {url}\n\n"

            q = Queue()
            self.subscribers.append(q)
            return Response(event_stream(q), mimetype="text/event-stream")

    def _notify_clients(self):
        for sub in self.subscribers:
            sub.put(self.current_video["url"])

    def set_video(self, youtube_url):
        """Change the video by providing a YouTube URL."""
        if youtube_url:
            try:
                embed_url = youtube_url.replace("watch?v=", "embed/").split("&")[0]
                embed_url += "?autoplay=1"
                self.current_video["url"] = embed_url
                self._notify_clients()
                print(f"[VideoServer] ✅ Video changed to: {embed_url}")
            except Exception as e:
                print(f"[VideoServer] ❌ Error processing URL: {e}")

    def _video_input_loop(self):
        while True:
            new_url = input("Enter new YouTube URL (or empty to skip): ").strip()
            if new_url:
                self.set_video(new_url)

    def start(self):
        """Start the server and input loop in background threads."""
        threading.Thread(target=self._video_input_loop, daemon=True).start()

        def run_flask():
            self.app.run(host=self.host, port=self.port, debug=False, threaded=True)

        threading.Thread(target=run_flask, daemon=True).start()
        print(f"[VideoServer] Server started at http://{self.host}:{self.port}")


# If run directly
if __name__ == '__main__':
    server = VideoServer()
    server.start()

    time.sleep(5)
    server.set_video("https://www.youtube.com/watch?v=7WABxk9DAuw")  # Change video programmatically

    # Keep script alive
    while True:
        server.set_video(input('Link: '))
