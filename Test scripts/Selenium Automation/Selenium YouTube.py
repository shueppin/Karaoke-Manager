# Using selenium~=4.33.0
from selenium import webdriver
from selenium.webdriver.edge.options import Options

from os import path, mkdir
from time import sleep


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

    def start_youtube_video(self, youtube_video_link, countdown=True):
        # Change the URL in the same tab
        self.driver.get(youtube_video_link)  # New URL

        # Execute the initial script to pause the video and wait until a result is received
        _ = self.driver.execute_async_script("""
            // Set the callback for Selenium
            const callback = arguments[arguments.length - 1];

            // Pause the video incase a user interaction has happened already
            const video = document.querySelector('video');
                if (video) {
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

        if countdown:
            # Start a countdown
            for i in range(5, 0, -1):
                print(f'Starting video in {i} seconds')
                sleep(1)

            self.click_fullscreen()

    def click_fullscreen(self):
        # Click the fullscreen button to start the video
        fullscreen_button = self.driver.find_element("css selector", ".ytp-fullscreen-button")
        fullscreen_button.click()

    def stop(self):
        self.driver.quit()


if __name__ == '__main__':
    browser = YouTubeWebdriver()
    sleep(5)
    browser.start_youtube_video('https://www.youtube.com/watch?v=dQw4w9WgXcQ')
    sleep(5)
    browser.start_youtube_video('https://www.youtube.com/watch?v=9jK-NcRmVcw')
    sleep(5)
    browser.stop()
