import tkinter as tk
from tkinter import messagebox
import json
import re
import os
from datetime import datetime


SONG_FILE = "songs.json"


class KaraokeApp:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Karaoke Manager")
        self.root.geometry("800x600")

        self.song_list = []
        self.current_song_data = None
        self.current_song_start_time = None
        self.edit_mode = False

        self.basic_font = ("Segoe UI", 11)
        self.re_pattern = re.compile(r'(https?://)?(www\.)?(youtube\.com|youtu\.be)/.+')

        # Load the song_list from the JSON
        self.load_songs()

        # Create the Widgets
        self.top_frame = tk.Frame(self.root)
        self.top_frame.pack(pady=10)

        self.play_button = tk.Button(self.top_frame, text="Play Next Song", font=("Segoe UI", 15), command=self.play_next_song)
        self.play_button.pack(side=tk.LEFT, padx=15)

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

        self.root.mainloop()

    def load_songs(self):
        if os.path.exists(SONG_FILE):
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

    def update_current_song_label(self):
        self.current_song_label.config(
            text=f"Now Playing: {self.current_song_data['name']} by {self.current_song_data['author']} (Singer: {self.current_song_data['person']})\nStarted at: {self.current_song_start_time}",
            fg="green"
        )

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

        # If there are any songs in the list set the current song to the newest one and display this
        if self.song_list:
            self.current_song_data = self.song_list[0]
            self.current_song_start_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            self.update_current_song_label()

        self.save_songs()
        self.update_song_list()


if __name__ == "__main__":
    KaraokeApp()
