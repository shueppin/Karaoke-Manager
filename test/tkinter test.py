import tkinter as tk
from tkinter import simpledialog, messagebox, filedialog, Toplevel, Label, Entry, Button
import json
import re
import os
from datetime import datetime


SONG_FILE = "songs.json"


class KaraokeApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Karaoke Manager")
        self.root.geometry("800x600")

        self.songs = []
        self.current_song = None
        self.current_song_start_time = None
        self.edit_mode = False

        self.load_songs()
        self.create_widgets()
        self.update_song_list()

    def create_widgets(self):
        self.top_frame = tk.Frame(self.root)
        self.top_frame.pack(pady=10)

        self.play_button = tk.Button(self.top_frame, text="Play Next Song", command=self.play_next_song)
        self.play_button.pack(side=tk.LEFT, padx=5)

        self.edit_button = tk.Button(self.top_frame, text="Edit Songs", command=self.toggle_edit_mode)
        self.edit_button.pack(side=tk.LEFT, padx=5)

        self.add_button = tk.Button(self.top_frame, text="Add New Song", command=self.add_song)
        self.add_button.pack(side=tk.LEFT, padx=5)

        self.current_song_label = tk.Label(self.root, text="", font=("Arial", 14), fg="blue")
        self.current_song_label.pack(pady=5)

        self.song_list_frame = tk.Frame(self.root)
        self.song_list_frame.pack()

        self.song_widgets = []

    def load_songs(self):
        if os.path.exists(SONG_FILE):
            with open(SONG_FILE, "r") as f:
                self.songs = json.load(f)

    def save_songs(self):
        with open(SONG_FILE, "w") as f:
            json.dump(self.songs, f, indent=4)

    def update_song_list(self):
        for widget in self.song_widgets:
            widget.destroy()
        self.song_widgets.clear()

        for index, song in enumerate(self.songs):
            text = f"{song['name']} by {song['author']} | Singer: {song['person']} | Link: {song['link']}"
            label_color = "green" if self.current_song and song == self.current_song else "black"
            label = tk.Label(self.song_list_frame, text=text, fg=label_color)
            label.grid(row=index, column=0, sticky="w")
            self.song_widgets.append(label)

            if self.edit_mode:
                edit_btn = tk.Button(self.song_list_frame, text="Edit", command=lambda i=index: self.edit_song(i))
                edit_btn.grid(row=index, column=1)
                del_btn = tk.Button(self.song_list_frame, text="Delete", command=lambda i=index: self.delete_song(i))
                del_btn.grid(row=index, column=2)
                up_btn = tk.Button(self.song_list_frame, text="↑", command=lambda i=index: self.move_song_up(i))
                up_btn.grid(row=index, column=3)
                down_btn = tk.Button(self.song_list_frame, text="↓", command=lambda i=index: self.move_song_down(i))
                down_btn.grid(row=index, column=4)
                self.song_widgets += [edit_btn, del_btn, up_btn, down_btn]

    def is_valid_youtube_link(self, link):
        pattern = re.compile(r'(https?://)?(www\.)?(youtube\.com|youtu\.be)/.+')
        return bool(pattern.match(link))

    def open_song_input_window(self, title, initial_data=None, callback=None):
        x = self.root.winfo_x()
        y = self.root.winfo_y()

        window = Toplevel()
        window.title(title)
        window.geometry(f"800x600+{x}+{y}")

        Label(window, text="Name of the person:").grid(row=0, column=0)
        person_entry = Entry(window)
        person_entry.grid(row=0, column=1)

        Label(window, text="Name of the song:").grid(row=1, column=0)
        name_entry = Entry(window)
        name_entry.grid(row=1, column=1)

        Label(window, text="Author of the song:").grid(row=2, column=0)
        author_entry = Entry(window)
        author_entry.grid(row=2, column=1)

        Label(window, text="Link to the song:").grid(row=3, column=0)
        link_entry = Entry(window)
        link_entry.grid(row=3, column=1)

        error_label = Label(window, text="", fg="red")
        error_label.grid(row=4, columnspan=2)

        if initial_data:
            person_entry.insert(0, initial_data['person'])
            name_entry.insert(0, initial_data['name'])
            author_entry.insert(0, initial_data['author'])
            link_entry.insert(0, initial_data['link'])

        def submit():
            person = person_entry.get()
            name = name_entry.get()
            author = author_entry.get()
            link = link_entry.get()

            if not self.is_valid_youtube_link(link):
                error_label.config(text="Invalid YouTube link. Please correct it.")
                return

            if callback:
                callback({"person": person, "name": name, "author": author, "link": link})
            window.destroy()

        Button(window, text="Submit", command=submit).grid(row=5, columnspan=2, pady=10)

    def add_song(self):
        self.edit_mode = False
        self.edit_button.config(relief=tk.RAISED)
        self.update_song_list()
        self.open_song_input_window("Add New Song", callback=self.add_song_callback)

    def add_song_callback(self, song):
        self.songs.append(song)
        self.save_songs()
        self.update_song_list()

    def toggle_edit_mode(self):
        self.edit_mode = not self.edit_mode
        self.edit_button.config(relief=tk.SUNKEN if self.edit_mode else tk.RAISED)
        self.update_song_list()

    def edit_song(self, index):
        self.open_song_input_window("Edit Song", initial_data=self.songs[index], callback=lambda data: self.edit_song_callback(index, data))

    def edit_song_callback(self, index, song):
        self.songs[index] = song
        self.save_songs()
        self.update_song_list()

    def delete_song(self, index):
        confirm = messagebox.askyesno("Confirm Delete", f"Are you sure you want to delete '{self.songs[index]['name']}'?")
        if confirm:
            del self.songs[index]
            self.save_songs()
            self.update_song_list()

    def move_song_up(self, index):
        if index > 0:
            self.songs[index], self.songs[index - 1] = self.songs[index - 1], self.songs[index]
            self.save_songs()
            self.update_song_list()

    def move_song_down(self, index):
        if index < len(self.songs) - 1:
            self.songs[index], self.songs[index + 1] = self.songs[index + 1], self.songs[index]
            self.save_songs()
            self.update_song_list()

    def play_next_song(self):
        if not self.songs:
            messagebox.showinfo("Info", "No songs in the list.")
            return

        self.edit_mode = False
        self.edit_button.config(relief=tk.RAISED)

        if self.current_song is not None:
            current_index = next((i for i, s in enumerate(self.songs) if s == self.current_song), None)
            if current_index is not None:
                remove = messagebox.askyesno("Remove Song", f"Remove current song '{self.current_song['name']}' from the list?")
                if remove:
                    del self.songs[current_index]
                else:
                    self.songs.append(self.songs.pop(current_index))

        if self.songs:
            self.current_song = self.songs[0]
            self.current_song_start_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            self.current_song_label.config(
                text=f"Now Playing: {self.current_song['name']} by {self.current_song['author']} (Singer: {self.current_song['person']})\nStarted at: {self.current_song_start_time}",
                fg="green"
            )

        self.save_songs()
        self.update_song_list()


if __name__ == "__main__":
    window = tk.Tk()
    app = KaraokeApp(window)
    window.mainloop()
