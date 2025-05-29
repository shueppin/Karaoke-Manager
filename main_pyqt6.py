import json
import re
from datetime import datetime
from os import path
import sys
import threading

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QLabel, QPushButton, QVBoxLayout, QHBoxLayout,
    QLineEdit, QDialog, QGridLayout, QMessageBox, QScrollArea
)
from PyQt6.QtCore import Qt

from flask import Flask, render_template_string, Response
from queue import Queue
import webbrowser


# Define as string so no extra file is needed
HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>Fullscreen Video Viewer</title>
    <style>
        html, body {
            margin: 0;
            height: 100%;
            overflow: hidden;
            background-color: black;
        }
        iframe {
            width: 100vw;
            height: 100vh;
            border: none;
        }
    </style>
</head>
<body>
    <iframe id="video"
        src="{{ video_url }}"
        allowfullscreen
        allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share"
        referrerpolicy="strict-origin-when-cross-origin"
        title="YouTube Video">
    </iframe>

    <script>
        const videoFrame = document.getElementById("video");
        const evtSource = new EventSource("/video-stream");

        evtSource.onmessage = function(event) {
            if (videoFrame.src !== event.data) {
                videoFrame.src = event.data;
            }
        };
    </script>
</body>
</html>
"""


SONG_FILE = "songs.json"


class VideoServer:
    def __init__(self, host='127.0.0.1', port=5000):
        # Define the variables and show a video on launch
        self.host = host
        self.port = port
        self.app = Flask(__name__)
        self.current_video = {"url": "https://www.youtube.com/embed/7WABxk9DAuw?autoplay=1"}
        self.subscribers = []
        self._setup_routes()
        self.server_thread = threading.Thread(target=self._run_flask, daemon=True)

    def _setup_routes(self):
        # Define all website paths
        @self.app.route('/')
        def index():
            return render_template_string(HTML_TEMPLATE, video_url=self.current_video["url"])

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

    def _run_flask(self):
        self.app.run(host=self.host, port=self.port, debug=False, threaded=True)

    def set_video(self, youtube_url):
        # Check if the server is alive
        if not self.server_thread.is_alive():
            raise RuntimeError('No server is running. Please start it first with VideoServer.start()')

        # Change the video of all clients by passing a valid YouTube URL to this function
        if youtube_url:
            try:
                embed_url = youtube_url.replace("watch?v=", "embed/").split("&")[0]
                embed_url += "?autoplay=1&cc_lang_policy=0&iv_load_policy=3"  # Remove the subtitles and make the video autoplay if possible
                self.current_video["url"] = embed_url
                self._notify_clients()
                print(f"[VideoServer] Video changed to: {embed_url}")
            except Exception as e:
                print(f"[VideoServer] Error processing URL: {e}")

    def start(self):
        # Start the server in the background
        self.server_thread.start()
        server_url = f"http://{self.host}:{self.port}"
        print(f"[VideoServer] Server started at {server_url}")
        return server_url

    """
    Stopping the server is only possible by exiting the whole script.
    """


class KaraokeApp(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setStyleSheet("""
            QWidget {
                background-color: #ffffff;
                color: #000000;
                font-family: Segoe UI, sans-serif;
                font-size: 11pt;
            }
            QPushButton {
                background-color: #f0f0f0;
                border: 1px solid #ccc;
                padding: 4px 8px;
            }
            QPushButton:hover {
                background-color: #e0e0e0;
            }
            QLineEdit {
                background-color: #ffffff;
                border: 1px solid #ccc;
                padding: 2px;
            }
            QLabel {
                font-size: 10pt;
            }
        """)

        # Initialize the YouTube Player
        self.video_server = VideoServer()
        server_url = self.video_server.start()
        webbrowser.open(server_url)  # Open the URL of the server in the browser

        self.setWindowTitle("Karaoke Manager")
        self.resize(800, 600)

        # Define some basic variables
        self.song_list = []
        self.current_song_data = None
        self.current_song_start_time = None
        self.edit_mode = False
        self.countdown_stop_event = threading.Event()  # This variable tells the script to try and stop the countdown
        self.countdown_thread = threading.Thread()

        self.basic_font = "Segoe UI"
        self.re_pattern = re.compile(r'(https?://)?(www\.)?(youtube\.com)/.+')

        # Load the song_list from the JSON
        self.load_songs()

        # Create the Widgets
        main_widget = QWidget()
        self.setCentralWidget(main_widget)

        main_layout = QVBoxLayout()
        main_widget.setLayout(main_layout)

        # Top control buttons
        top_layout = QHBoxLayout()
        self.play_button = QPushButton("Play Next Song")
        self.play_button.clicked.connect(self.play_next_song)
        top_layout.addWidget(self.play_button)

        self.add_button = QPushButton("Add New Song")
        self.add_button.clicked.connect(self.add_song)
        top_layout.addWidget(self.add_button)

        self.edit_button = QPushButton("Edit Songs")
        self.edit_button.setCheckable(True)
        self.edit_button.clicked.connect(self.toggle_edit_mode)
        top_layout.addWidget(self.edit_button)

        main_layout.addLayout(top_layout)

        self.current_song_label = QLabel("")
        main_layout.addWidget(self.current_song_label)

        # Scrollable song list
        self.song_list_container = QWidget()
        self.song_list_layout = QVBoxLayout()
        self.song_list_container.setLayout(self.song_list_layout)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(self.song_list_container)
        main_layout.addWidget(scroll)

        self.song_widgets = []
        # Create all widgets for all songs

        self.update_song_list()

    def load_songs(self):
        if path.exists(SONG_FILE):
            with open(SONG_FILE) as file:
                self.song_list = json.load(file)

    def save_songs(self):
        with open(SONG_FILE, "w") as file:
            json.dump(self.song_list, file, indent=4)

    def update_song_list(self):
        # Clear existing widgets
        for widget in self.song_widgets:
            widget.deleteLater()
        self.song_widgets.clear()

        # Remove all existing items (including spacers/stretch) from the layout
        while self.song_list_layout.count():
            item = self.song_list_layout.takeAt(0)
            if item.widget():
                item.widget().setParent(None)
            # No need to do anything for spacers here, they are removed by takeAt()

        for index, song_data in enumerate(self.song_list):
            song_row_widget = QWidget()
            song_row_layout = QHBoxLayout(song_row_widget)
            song_row_layout.setContentsMargins(0, 0, 0, 0)
            song_row_layout.setSpacing(5)

            text = f'Singer: {song_data["person"]} | "{song_data["name"]}" by {song_data["author"]} | Link: {song_data["link"]}'
            label_color = "green" if song_data == self.current_song_data else "black"
            label = QLabel(text)
            label.setStyleSheet(f"color: {label_color}; font-size: 10pt;")
            song_row_layout.addWidget(label, stretch=1)

            if self.edit_mode:
                edit_button = QPushButton("Edit")
                edit_button.clicked.connect(lambda _, i=index: self.edit_song(i))
                song_row_layout.addWidget(edit_button)

                del_button = QPushButton("Delete")
                del_button.clicked.connect(lambda _, i=index: self.delete_song(i))
                song_row_layout.addWidget(del_button)

                up_button = QPushButton("↑")
                up_button.clicked.connect(lambda _, i=index: self.move_song_up(i))
                song_row_layout.addWidget(up_button)

                down_button = QPushButton("↓")
                down_button.clicked.connect(lambda _, i=index: self.move_song_down(i))
                song_row_layout.addWidget(down_button)

            self.song_list_layout.addWidget(song_row_widget)
            self.song_widgets.append(song_row_widget)

        # Add vertical stretch (placeholder) to push all content to top, only one stretch at the bottom
        self.song_list_layout.addStretch(1)

    def is_valid_youtube_link(self, link):
        return bool(self.re_pattern.match(link))

    def open_song_input_window(self, initial_song_data=None, song_index=None):
        dialog = QDialog(self)
        dialog.setWindowTitle("Edit Song" if initial_song_data else "Add New Song")  # If there is initial data, it is in edit mode.
        layout = QGridLayout(dialog)

        layout.addWidget(QLabel("Name of the person:"), 0, 0)
        person_entry = QLineEdit()
        layout.addWidget(person_entry, 0, 1)

        layout.addWidget(QLabel("Name of the song:"), 1, 0)
        name_entry = QLineEdit()
        layout.addWidget(name_entry, 1, 1)

        layout.addWidget(QLabel("Author of the song:"), 2, 0)
        author_entry = QLineEdit()
        layout.addWidget(author_entry, 2, 1)

        layout.addWidget(QLabel("Link to the song:"), 3, 0)
        link_entry = QLineEdit()
        layout.addWidget(link_entry, 3, 1)

        error_label = QLabel("")
        error_label.setStyleSheet("color: red;")
        layout.addWidget(error_label, 4, 0, 1, 2)

        # If data already exists use this data.
        if initial_song_data:
            person_entry.setText(initial_song_data["person"])
            name_entry.setText(initial_song_data["name"])
            author_entry.setText(initial_song_data["author"])
            link_entry.setText(initial_song_data["link"])

        def save():
            # Get the data of all the entries
            person = person_entry.text()
            name = name_entry.text()
            author = author_entry.text()
            link = link_entry.text()

            # Check for a valid link, if wrong show an error
            if not self.is_valid_youtube_link(link):
                error_label.setText("Invalid YouTube link. Please correct it.")
                return

            new_song_data = {"person": person, "name": name, "author": author, "link": link}
            # If it is in edit mode (there is initial data) modify the data at the known index and modify the label and the current song if needed
            if initial_song_data:
                if initial_song_data == self.current_song_data:
                    self.current_song_data = new_song_data
                    self.update_current_song_label()

                self.song_list[song_index] = new_song_data
            else:
                self.song_list.append(new_song_data)

            # Save the song list and modify the displayed list
            self.save_songs()
            self.update_song_list()
            dialog.accept()

        save_btn = QPushButton("Save")
        save_btn.clicked.connect(save)
        layout.addWidget(save_btn, 5, 0, 1, 2)

        dialog.exec()

    def add_song(self):
        # Disable the edit mode if it is active
        self.edit_mode = False
        self.edit_button.setChecked(False)
        self.update_song_list()

        # Create a new song
        self.open_song_input_window()

    def toggle_edit_mode(self):
        # This activates/deactivates the edit mode and changes the state of the button
        self.edit_mode = self.edit_button.isChecked()
        self.update_song_list()

    def edit_song(self, index):
        self.open_song_input_window(initial_song_data=self.song_list[index], song_index=index)

    def delete_song(self, index):
        # Ask for confirmation
        reply = QMessageBox.question(self, "Confirm Delete",
                                     f'Are you sure you want to delete "{self.song_list[index]["name"]}", sung by "{self.song_list[index]["person"]}"?',
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            del self.song_list[index]
            self.save_songs()
            self.update_song_list()

    # Move the song up or down the list
    def move_song_up(self, index):
        if index > 0:
            self.song_list[index], self.song_list[index - 1] = self.song_list[index - 1], self.song_list[index]
            self.save_songs()
            self.update_song_list()

    def move_song_down(self, index):
        if index < len(self.song_list) - 1:
            self.song_list[index], self.song_list[index + 1] = self.song_list[index + 1], self.song_list[index]
            self.save_songs()
            self.update_song_list()

    def get_current_song_index(self):
        # Find the index of the actual song, or otherwise return None
        for index, song in enumerate(self.song_list):
            if song == self.current_song_data:
                return index
        return None

    def update_current_song_label(self):
        if self.current_song_data:
            self.current_song_label.setText(
                f'Now Playing: "{self.current_song_data["name"]}" by "{self.current_song_data["author"]}" (Singer: {self.current_song_data["person"]}) \nStarted at: {self.current_song_start_time}'
            )

    def play_next_song(self):
        # When the list is empty, show an information message
        if not self.song_list:
            QMessageBox.information(self, "Info", "No songs in the list.")
            return

        # Disable the edit mode incase it is active
        self.edit_mode = False
        self.edit_button.setChecked(False)

        # If a song is currently being played, get its index and ask whether the song should be removed from the list or just appended at the end of the list
        if self.current_song_data is not None:
            current_index = self.get_current_song_index()
            if current_index is not None:
                remove = QMessageBox.question(self, "Remove Song",
                                              f'Remove current song "{self.current_song_data["name"]}"?',
                                              QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
                if remove == QMessageBox.StandardButton.Yes:
                    del self.song_list[current_index]
                else:
                    self.song_list.append(self.song_list.pop(current_index))

        # If there are any songs in the list set the current song to the newest one, send the song to the server and set the label text
        if self.song_list:
            self.current_song_data = self.song_list[0]
            self.video_server.set_video(self.current_song_data['link'])

            self.current_song_start_time = datetime.now().strftime('%H:%M:%S')
            self.update_current_song_label()

        self.save_songs()
        self.update_song_list()

    def closeEvent(self, event):
        reply = QMessageBox.question(self, "Quit", "Do you really want to quit? \n(This will also stop the webserver)",
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            event.accept()
            sys.exit()
        else:
            event.ignore()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = KaraokeApp()
    window.show()
    sys.exit(app.exec())
