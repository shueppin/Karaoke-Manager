import json
import re
from datetime import datetime
from os import path, mkdir
from time import sleep
import threading

import tkinter as tk
from tkinter import messagebox

# Using selenium~=4.33.0
from selenium import webdriver
from selenium.webdriver.edge.options import Options


SONG_FILE = "songs.json"


class YouTubeWebdriver:
    def __init__(self, webdriver_type='Edge', maximize=True):
        # Get the directory where the Selenium data should be stored or create it
        script_dir = path.dirname(path.abspath(__file__))
        selenium_data_dir = path.join(script_dir, 'selenium_data')

        if not path.exists(selenium_data_dir):
            mkdir(selenium_data_dir)

        # Set the options to use this custom data directory
        options = Options()
        options.add_argument(f"user-data-dir={selenium_data_dir}")
        options.add_argument("--autoplay-policy=no-user-gesture-required")

        # Initialize the webdriver
        if webdriver_type == 'Edge':
            self.driver = webdriver.Edge(options=options)
        elif webdriver_type == 'Chrome':
            self.driver = webdriver.Chrome(options=options)
        elif webdriver_type == 'Firefox':
            self.driver = webdriver.Firefox(options=options)

        # Startup the driver and YouTube to allow browser extension scripts to load fully
        self.driver.get("https://youtube.com")  # Initial URL

        if maximize:
            self.driver.maximize_window()

    def start_youtube_video(self, youtube_video_link):
        # Change the URL in the same tab
        self.driver.get(youtube_video_link)  # New URL

        # Execute the initial script to pause the video and wait until a result is received
        _ = self.driver.execute_async_script("""
            // Set the callback for Selenium
            const callback = arguments[arguments.length - 1];

            // Pause the video incase a user interaction has happened already
            const video = document.querySelector('video');
                if (video) {
                    video.mute = true
                    video.pause();
                    video.autoplay = false;
                    video.removeAttribute('autoplay');
                }

            // Poll for YouTube internal player object to check when the video is fully loaded and send the callback to Selenium
            const checkYTPlayer = setInterval(() => {
                if (window.ytplayer && window.ytplayer.config) {
                    clearInterval(checkYTPlayer);
                    callback('Player is ready');
                }
            }, 100);
        """)

    def click_fullscreen(self):
        # Click the fullscreen button to start the video
        fullscreen_button = self.driver.find_element("css selector", ".ytp-fullscreen-button")
        fullscreen_button.click()

    def stop(self):
        self.driver.quit()


class KaraokeApp:
    def __init__(self):
        # Initialize the YouTube Player
        self.youtube_player = YouTubeWebdriver()

        self.root = tk.Tk()
        self.root.title("Karaoke Manager")
        self.root.geometry("800x600")

        # Set up the protocol for the window close event
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

        # Define some basic variables
        self.song_list = []
        self.current_song_data = None
        self.current_song_start_time = None
        self.edit_mode = False
        self.countdown_stop_event = threading.Event()  # This variable tells the script to try and stop the countdown
        self.countdown_thread = threading.Thread()

        self.basic_font = ("Segoe UI", 11)
        self.re_pattern = re.compile(r'(https?://)?(www\.)?(youtube\.com|youtu\.be)/.+')

        # Load the song_list from the JSON
        self.load_songs()

        # Create the Widgets
        self.top_frame = tk.Frame(self.root)
        self.top_frame.pack(pady=10)

        # This is the button which plays the next song or stops the countdown when a new song is started.
        self.play_and_stop_countdown_button = tk.Button(self.top_frame, text="Play Next Song", font=("Segoe UI", 15), command=self.play_and_stop_countdown_button_action)
        self.play_and_stop_countdown_button.pack(side=tk.LEFT, padx=15)

        self.add_button = tk.Button(self.top_frame, text="Add New Song", font=("Segoe UI", 15), command=self.add_song)
        self.add_button.pack(side=tk.LEFT, padx=15)

        self.edit_button = tk.Button(self.top_frame, text="Edit Songs", font=("Segoe UI", 15), command=self.toggle_edit_mode)
        self.edit_button.pack(side=tk.LEFT, padx=15)

        self.current_song_label = tk.Label(self.root, text="", font=("Segoe UI", 13), fg="green")
        self.current_song_label.pack(pady=5)

        self.song_list_frame = tk.Frame(self.root)
        self.song_list_frame.pack()

        self.song_widgets = []

        # Create all the widgets for all the song_list
        self.update_song_list()

        # Main tkinter interaction loop
        self.root.mainloop()

    def load_songs(self):
        if path.exists(SONG_FILE):
            with open(SONG_FILE) as file:
                self.song_list = json.load(file)

    def save_songs(self):
        with open(SONG_FILE, "w") as file:
            json.dump(self.song_list, file, indent=4)

    def update_song_list(self):
        # Remove all the old song_list
        for widget in self.song_widgets:
            widget.destroy()
        self.song_widgets.clear()

        # Go through all songs in the song list and create a widget for them
        for index, song_data in enumerate(self.song_list):
            text = f'Singer: {song_data['person']} | "{song_data['name']}" by {song_data['author']} | Link: {song_data['link']}'
            label_color = "green" if song_data == self.current_song_data else "black"
            label = tk.Label(self.song_list_frame, text=text, fg=label_color, font=self.basic_font)
            label.grid(row=index, column=0, sticky="w")
            self.song_widgets.append(label)

            # Make column 0 expand so the edit buttons are guaranteed to be displayed
            self.song_list_frame.grid_columnconfigure(0, weight=1)

            # Add more buttons in the edit mode and add them all to the song widgets
            if self.edit_mode:
                edit_button = tk.Button(self.song_list_frame, text="Edit", command=lambda i=index: self.edit_song(i))
                edit_button.grid(row=index, column=1)
                del_button = tk.Button(self.song_list_frame, text="Delete", command=lambda i=index: self.delete_song(i))
                del_button.grid(row=index, column=2)
                up_button = tk.Button(self.song_list_frame, text="↑", command=lambda i=index: self.move_song_up(i))
                up_button.grid(row=index, column=3)
                down_button = tk.Button(self.song_list_frame, text="↓", command=lambda i=index: self.move_song_down(i))
                down_button.grid(row=index, column=4)
                self.song_widgets += [edit_button, del_button, up_button, down_button]

    def is_valid_youtube_link(self, link):
        return bool(self.re_pattern.match(link))

    def open_song_input_window(self, initial_song_data=None, song_index=None):
        # Define the width and height of the window, so it is below the y-center of the main window but centered on the x-axis of the main window
        width = round(self.root.winfo_width() / 2)
        height = round(self.root.winfo_height() / 2)
        x = round(self.root.winfo_x() + 0.5 * width)
        y = round(self.root.winfo_y() + height)

        # Define the window with a title according to the mode it is in (either add or edit)
        input_window = tk.Toplevel()
        input_window.geometry(f"{width}x{height}+{x}+{y}")

        # If there is initial data, it is in edit mode.
        if initial_song_data:
            input_window.title("Edit Song")
        else:
            input_window.title("Add New Song")

        # Define all labels and entry boxes
        tk.Label(input_window, text="Name of the person:", font=self.basic_font).grid(row=0, column=0, sticky="w")
        person_entry = tk.Entry(input_window, font=self.basic_font)
        person_entry.grid(row=0, column=1, sticky="ew")

        tk.Label(input_window, text="Name of the song:", font=self.basic_font).grid(row=1, column=0, sticky="w")
        name_entry = tk.Entry(input_window, font=self.basic_font)
        name_entry.grid(row=1, column=1, sticky="ew")

        tk.Label(input_window, text="Author of the song:", font=self.basic_font).grid(row=2, column=0, sticky="w")
        author_entry = tk.Entry(input_window, font=self.basic_font)
        author_entry.grid(row=2, column=1, sticky="ew")

        tk.Label(input_window, text="Link to the song:", font=self.basic_font).grid(row=3, column=0, sticky="w")
        link_entry = tk.Entry(input_window, font=self.basic_font)
        link_entry.grid(row=3, column=1, sticky="ew")

        error_label = tk.Label(input_window, text="", fg="red", font=self.basic_font)
        error_label.grid(row=4, columnspan=2)

        # Make column 1 expand so the width of the entries is according to the window with
        input_window.grid_columnconfigure(1, weight=1)

        # If data already exists use this data.
        if initial_song_data:
            person_entry.insert(0, initial_song_data['person'])
            name_entry.insert(0, initial_song_data['name'])
            author_entry.insert(0, initial_song_data['author'])
            link_entry.insert(0, initial_song_data['link'])

        def save():
            # Get the data of all the entries
            person = person_entry.get()
            name = name_entry.get()
            author = author_entry.get()
            link = link_entry.get()

            # Check for a valid link, if wrong show an error
            if not self.is_valid_youtube_link(link):
                error_label.config(text="Invalid YouTube link. Please correct it.")
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

            # Destroy the input window
            input_window.destroy()

        tk.Button(input_window, text="Save", font=("Segoe UI", 13), command=save).grid(row=5, columnspan=2, pady=10)

    def add_song(self):
        # Disable the edit mode if it is active
        self.edit_mode = False
        self.edit_button.config(relief=tk.RAISED)
        self.update_song_list()

        # Create a new song
        self.open_song_input_window()

    def toggle_edit_mode(self):
        # This activates/deactivates the edit mode and changes the state of the button
        self.edit_mode = not self.edit_mode
        self.edit_button.config(relief=tk.SUNKEN if self.edit_mode else tk.RAISED)
        self.update_song_list()

    def edit_song(self, index):
        self.open_song_input_window(initial_song_data=self.song_list[index], song_index=index)

    def delete_song(self, index):
        # Ask for confirmation
        confirm = messagebox.askyesno("Confirm Delete", f'Are you sure you want to delete "{self.song_list[index]['name']}", sung by "{self.song_list[index]['person']}"?')
        if confirm:
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

    def update_current_song_label(self, countdown=0):
        if countdown:
            text = f'"{self.current_song_data['name']}" by "{self.current_song_data['author']}" (Singer: {self.current_song_data['person']}) \nStarting in {countdown} seconds.'
        else:
            text = f'"{self.current_song_data['name']}" by "{self.current_song_data['author']}" (Singer: {self.current_song_data['person']}) \nStarted at: {self.current_song_start_time}'

        self.current_song_label.config(
            text=text,
            fg="green"
        )

    def play_and_stop_countdown_button_action(self):
        # If the Script is counting down or starting the Video it should try to stop this from happening.
        if self.countdown_thread.is_alive():
            # If the thread is already being stopped then just show a message
            if self.countdown_stop_event.is_set():
                messagebox.showinfo("Info", "Wait shortly between actions.")
                return

            # Otherwise try to stop the thread by setting the stop event
            self.countdown_stop_event.set()

        # If there is no countdown or the video is not being started then just play the next song
        else:
            self.play_next_song()

    def play_next_song(self):
        # When the list is empty, show an information message
        if not self.song_list:
            messagebox.showinfo("Info", "No songs in the list.")
            return

        # Disable the edit mode incase it is active
        self.edit_mode = False
        self.edit_button.config(relief=tk.RAISED)

        # If a song is currently being played, get its index and ask whether the song should be removed from the list or just appended at the end of the list
        if self.current_song_data is not None:
            current_index = self.get_current_song_index()
            if current_index is not None:
                remove = messagebox.askyesno("Remove Song", f'Remove current song "{self.current_song_data['name']}", sung by "{self.current_song_data['name']}" from the list?')
                if remove:
                    del self.song_list[current_index]
                else:
                    self.song_list.append(self.song_list.pop(current_index))

        # If there are any songs in the list set the current song to the newest one, set the new button text and start the countdown
        if self.song_list:
            self.current_song_data = self.song_list[0]
            self.play_and_stop_countdown_button.config(text='Stop Countdown')
            self.countdown_thread = threading.Thread(target=self.start_video_with_countdown)  # Set the thread that starts the countdown for the video
            self.countdown_thread.start()

        self.save_songs()
        self.update_song_list()

    def start_video_with_countdown(self):
        def countdown_stopped():
            self.play_and_stop_countdown_button.config(text='Play Next Song')
            self.countdown_stop_event.clear()

        # Open the YouTube video for the current song
        link = self.current_song_data['link']
        self.youtube_player.start_youtube_video(link)

        # If it should stop the thread then just exit the function
        if self.countdown_stop_event.is_set():
            countdown_stopped()
            return

        # Run the countdown, update the label every second and check if it is interrupted
        for countdown_seconds in range(5, 0, -1):
            self.update_current_song_label(countdown=countdown_seconds)
            sleep(1)

            if self.countdown_stop_event.is_set():
                countdown_stopped()
                return

        # Update the label
        self.current_song_start_time = datetime.now().strftime('%H:%M:%S')
        self.update_current_song_label()

        # Start the YouTube video by activating the fullscreen
        self.youtube_player.click_fullscreen()

        # Reset the stop command incase it was set in the meantime
        countdown_stopped()

    def on_closing(self):
        # Show a confirmation dialog
        if messagebox.askyesno("Quit", "Do you really want to quit? \n(This window will close shortly after the browser is closed)"):
            self.youtube_player.stop()  # Stop the browser
            self.root.destroy()  # Close the window


if __name__ == "__main__":
    KaraokeApp()
