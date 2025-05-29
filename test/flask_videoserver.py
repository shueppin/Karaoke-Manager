from flask import Flask, render_template, Response
import threading
from queue import Queue
import time


class VideoServer:
    def __init__(self, host='127.0.0.1', port=5000):
        # Define the variables and show a video on launch
        self.host = host
        self.port = port
        self.app = Flask(__name__)
        self.current_video = {"url": "https://www.youtube.com/embed/7WABxk9DAuw?autoplay=1"}
        self.subscribers = []
        self._setup_routes()

    def _setup_routes(self):
        # Define all website paths
        @self.app.route('/')
        def index():
            return render_template('index.html', video_url=self.current_video["url"])

        # Video Stream Path is responsible for providing the communication with the clients
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
        # Change the video of all clients by passing a valid YouTube URL to this function
        if youtube_url:
            try:
                embed_url = youtube_url.replace("watch?v=", "embed/").split("&")[0]
                embed_url += "?autoplay=1"
                self.current_video["url"] = embed_url
                self._notify_clients()
                print(f"[VideoServer] Video changed to: {embed_url}")
            except Exception as e:
                print(f"[VideoServer] Error processing URL: {e}")

    def start(self):
        # Start the server in the background
        def run_flask():
            self.app.run(host=self.host, port=self.port, debug=False, threaded=True)

        threading.Thread(target=run_flask, daemon=True).start()
        print(f"[VideoServer] Server started at http://{self.host}:{self.port}")

    """
    Stopping the server is only possible by exiting the whole script.
    """


if __name__ == '__main__':
    # Startup the server and wait
    server = VideoServer()
    server.start()

    time.sleep(5)

    # Provide a simple CLI
    while True:
        command = input('Enter new link or write "stop" to stop the server: ')
        if command == 'stop':
            exit()
        elif command.startswith('https://www.youtube.com/watch?v='):
            server.set_video(command)
