import boto3 as AWS
from src.Files.credentials import USERNAME, SPOTIPY_CLIENT_ID, SPOTIPY_CLIENT_SECRET, SPOTIPY_REDIRECT_URI, AWS_ACCESS_KEY,\
    AWS_SECRET_KEY
from src.SpotifyLights.dynamodb_client import DynamoDBClient
import numpy as np
from scipy.interpolate import interp1d
import spotipy
import spotipy.util as util
import sys
import threading
import time
from src.SpotifyLights.Visualizations.LoudnessLengthEdgeFadeVisualizer import LoudnessLengthEdgeFadeVisualizer
from src.SpotifyLights.Visualizations.LoudnessLengthWithPitchVisualizer import LoudnessLengthWithPitchVisualizer

__author__ = "Yusuf Sezer"


class SpotifyVisualizer:
    """A class that allows for multi-threaded music visualization via the Spotify API, a Raspberry Pi, and an LED
    strip. When invoked in developer mode, a virtual LED strip will be opened in a new window!

    This code was developed and tested on a 240-pixel (4 meter) Adafruit Dotstar LED strip, a Raspberry Pi 3 Model B
    and my personal Spotify account. After initializing an instance of this class, simply call visualize() to begin
    visualization (alternatively, simply run this module). Visualization will continue until the program is interrupted
    or terminated. There are 4 threads: one for visualization, one for periodically syncing the playback position with
    the Spotify API, one for loading chunks of track data, and one to periodically check if the user's current track has
    changed.

    Currently, loudness and pitch data are used to generate and display visualizations on the LED strip. Loudness is
    used to determine how many pixels to light (growing from the center of the strip towards the ends). At any given
    moment, the lit part of the strip is segmented into 12 equal-length zones (one zone for each of the 12 major pitch
    keys). Each zone fades from start_color to its corresponding end color in end_colors. If the pitch key corresponding
    to a zone is very strong (high presence), that zone will be set to its end color. If the pitch key corresponding to
    a zone is very weak, then the zone will be set to start_color. If the pitch key corresponding to a zone is of
    intermediate strength, then the zone will be set to a color value between start_color and its end color.
    Additionally, A fade effect is applied to the ends of each zone; the color of the middle pixel of a zone will be set
    purely based on the strength of the corresponding pitch. Pixels towards the end of each zone, however, will fade
    back towards start_color.

    Usage:
        python3 spotify_visualizer.py
    Developer mode:
        python3 spotify_visualizer.py True

    Args:
        visualizer (Visualizer): The visualizer object that determines how the lights will be animated. It
            also holds information about the device being run on.
        loading_anim_visualizer (Animation): The animation object that displays a loading animation.

    Attributes:
            buffer_lock (threading.Lock): a lock for accessing/modifying the interpolated function buffers.
            data_segments (list): data segments to be parsed and analyzed (fetched from Spotify API).
            interpolated_loudness_buffer (list): producer-consumer buffer holding interpolated loudness functions.
            interpolated_pitch_buffer (list): producer-consumer buffer holding lists of interpolated pitch functions.
            loading_animator (Animator): a loading bar animator that replaces the visualizer when track is paused or loading.
            permission_scopes (str): a space-separated string of the required permission scopes over the user's account.
            playback_pos (float): the current playback position (offset into track in seconds) of the visualization.
            pos_lock (threading.Lock): a lock for accessing/modifying playback_pos.
            should_terminate (bool): a variable watched by all child threads (child threads exit if set to True).
            sp_gen (Spotify): Spotify object to handle main thread's interaction with the Spotify API.
            sp_load (Spotify): Spotify object to handle data loading thread's interaction with the Spotify API.
            sp_skip (Spotify): Spotify object to handle skip detection thread's interaction with the Spotify API.
            sp_sync (Spotify): Spotify object to handle synchronization thread's interaction with the Spotify API.
            sp_vis (Spotify): Spotify object to handle visualization thread's interaction with the Spotify API.
            start_color (tuple): a 3-tuple of ints for the RGB value representing the start color of the pitch gradient.
            track (dict): contains information about the track that is being visualized.
            track_duration (float): the duration in seconds of the track that is being visualized.
            visualizer (Visualizer): the visualization that holds the logic for the animation to be used.
    """

    def __init__(self, visualizer, loading_animator, auth_manager):
        self.buffer_lock = threading.Lock()
        self.data_segments = []
        self.interpolated_loudness_buffer = []
        self.interpolated_pitch_buffer = []
        self.is_playing = True
        self.loading_animator = loading_animator
        self.permission_scopes = "user-modify-playback-state user-read-currently-playing user-read-playback-state"
        self.playback_pos = 0
        self.pos_lock = threading.Lock()
        self.should_terminate = False
        self.song_ended = False
        self.sp_gen = self.sp_load = self.sp_skip = self.sp_sync = self.sp_vis = None
        self.start_color = (0, 0, 255)
        self.track = None
        self.track_duration = None
        self.visualizer = visualizer
        self.auth_manager = auth_manager

    def authorize(self):
        """Handle the authorization workflow for the Spotify API.
        """
        self.sp_gen = spotipy.Spotify(auth_manager=self.auth_manager)
        self.sp_vis = spotipy.Spotify(auth_manager=self.auth_manager)
        self.sp_sync = spotipy.Spotify(auth_manager=self.auth_manager)
        self.sp_load = spotipy.Spotify(auth_manager=self.auth_manager)
        self.sp_skip = spotipy.Spotify(auth_manager=self.auth_manager)
        self.sp_pause = spotipy.Spotify(auth_manager=self.auth_manager)
        text = "Successfully connected to {}'s account.".format(self.sp_gen.me()["display_name"])
        print(SpotifyVisualizer._make_text_effect(text, ["green"]))

    def is_running(self):
        return not self.should_terminate

    def get_track(self):
        """Fetches current track (waits for a track if necessary), starts it from beginning, and loads some track data.
        """
        text = "Waiting for an active Spotify track to start visualization."
        print(SpotifyVisualizer._make_text_effect(text, ["green", "bold"]))
        while not self.track:
            self.track = self.sp_gen.current_user_playing_track()
            time.sleep(1)
        track_name = self.track["item"]["name"]
        artists = ', '.join((artist["name"] for artist in self.track["item"]["artists"]))
        text = "Loaded track: {} by {}.".format(track_name, artists)
        print(SpotifyVisualizer._make_text_effect(text, ["green"]))
        self.track_duration = self.track["item"]["duration_ms"] / 1000
        self.is_playing = self.track["is_playing"]
        # self._load_track_data()

    def sync(self):
        """Syncs visualizer with Spotify playback. Called asynchronously (worker thread).
        """
        spotify_response = None
        while not spotify_response:
            spotify_response = self.sp_sync.current_user_playing_track()
            time.sleep(0.5)
        track_progress = spotify_response["progress_ms"] / 1000
        text = "Syncing track to position: {}. \r".format(track_progress)
        sys.stdout.write(SpotifyVisualizer._make_text_effect(text, ["green", "bold"]))
        sys.stdout.flush()
        self.pos_lock.acquire()
        self.playback_pos = track_progress
        self.pos_lock.release()

    def launch_visualizer(self):
        """Coordinate visualization by spawning the appropriate threads.

        There are 4 threads: one for visualization, one for periodically syncing the playback position with the Spotify
        API, one for loading chunks of track data, and one to periodically check if the user's current track has
        changed.
        """
        self.authorize()
        while not self.should_terminate:
            self._reset()
            self.get_track()

            # Start threads and wait for them to exit
            threads = [
                threading.Thread(target=self._visualize, name="[VISUALIZER] visualize_thread"),
                threading.Thread(target=self._continue_loading_data, name="[VISUALIZER] data_load_thread"),
                threading.Thread(target=self._continue_syncing, name="[VISUALIZER] sync_thread"),
                threading.Thread(target=self._continue_checking_if_skip, name="[VISUALIZER] skipping_thread"),
                threading.Thread(target=self._continue_checking_if_paused, name="[VISUALIZER] pause_thread")
            ]
            for thread in threads:
                thread.start()
            text = "Started visualization."
            print(SpotifyVisualizer._make_text_effect(text, ["green"]))
            for thread in threads:
                thread.join()

            self.visualizer.reset()
            text = "Visualization finished."
            
            print(SpotifyVisualizer._make_text_effect(text, ["green"]))

    def terminate_visualizer(self):
        """ Send a signal to kill all threads.

        Sends a signal to all subthreads and the main visualizer thread that
        kills them. This is used if an update is required.

        """
        self.should_terminate = True
        self.song_ended = True

    def _continue_checking_if_paused(self, wait=0.33):
        """Continuously checks if user's playback is paused, and updates self.is_playing accordingly.

        If the user's playback is paused, we should display an animation on the strip until playback resumes.

        Args:
            wait (float): the amount of time in seconds to wait between each check.
        """
        while not self.song_ended:
            try:
                self.is_playing = self.sp_pause.current_playback()["is_playing"]
            except:
                text = "Error occurred while checking if playback is paused...retrying in {} seconds.".format(wait)
                print(SpotifyVisualizer._make_text_effect(text, ["red", "bold"]))

    def _continue_checking_if_skip(self, wait=0.33):
        """Continuously checks if the user's playing track has changed. Called asynchronously (worker thread).

        If the user's currently playing track has changed (is different from track), then this function pauses the
        user's playback and sets should_terminate to True, resulting in the termination of all worker threads.

        Args:
            wait (float): the amount of time in seconds to wait between each check.
        """
        track = self.track
        while track["item"]["id"] == self.track["item"]["id"]:
            if self.song_ended:
                text = "Killing skip checking thread. (FORCE)"
                print(SpotifyVisualizer._make_text_effect(text, ["red", "bold"]))
                exit(0)
            try:
                spotify_response = self.sp_skip.current_user_playing_track()
                assert(spotify_response is not None)
                track = spotify_response
            except:
                text = "Error occurred while checking if track has changed...retrying in {} seconds.".format(wait)
                print(SpotifyVisualizer._make_text_effect(text, ["red", "bold"]))
            time.sleep(wait)
        self.song_ended = True
        text = "A skip has occurred."
        print(SpotifyVisualizer._make_text_effect(text, ["blue", "bold"]))

    def _continue_loading_data(self, wait=0.01):
        """Continuously loads and prepares chunks of data. Called asynchronously (worker thread).

        Args:
            wait (float): the amount of time in seconds to wait between each call to _load_track_data().
        """
        # If necessary, get audio data for the track from the Spotify API and pad data to cover the full track length
        if not self.data_segments:
            analysis = self.sp_load.audio_analysis(self.track["item"]["id"])
            self.data_segments.append(
                {
                    "start": -0.1,
                    "loudness_start": -25.0,
                    "pitches": 12*[0]
                }
            )
            self.data_segments += analysis["segments"]
            self.data_segments.append(
                {
                    "start": self.track_duration + 0.1,
                    "loudness_start": -25.0, "pitches": 12*[0]
                }
            )

        # Continue preparing track data until self.data_segments is exhausted
        while len(self.data_segments) != 0 and not self.song_ended:
            try:
                self._load_track_data()
            except:
                text = "Error occurred while loading data chunk...retrying in {} seconds.".format(wait)
                print(SpotifyVisualizer._make_text_effect(text, ["red", "bold"]))
            time.sleep(wait)
        text = "Killing data loading thread."
        print(SpotifyVisualizer._make_text_effect(text, ["red", "bold"]))
        exit(0)

    def _continue_syncing(self, wait=0.05):
        """Repeatedly syncs visualization playback position with the Spotify API.

        Args:
            wait (float): the amount of time in seconds to wait between each sync.
        """
        pos = self.playback_pos
        while round(self.track_duration - pos) != 0 and not self.song_ended:
            try:
                self.sync()
            except:
                text = "Error occurred while attempting to sync...retrying in {} seconds.".format(wait)
                print(SpotifyVisualizer._make_text_effect(text, ["red", "bold"]))
            time.sleep(wait)
            pos = self.playback_pos
        text = "Killing synchronization thread."
        print(SpotifyVisualizer._make_text_effect(text, ["red", "bold"]))
        exit(0)

    def _get_buffers_for_pos(self, pos):
        """Find the interpolated functions that have the specified position within their bounds via binary search.

        Args:
            pos (float): the playback position to find interpolated functions for.

        Returns:
             a tuple of interp1d objects (loudness and pitch functions) or None if search fails.
        """
        self.buffer_lock.acquire()

        # Binary search for interpolated loudness and pitch functions
        start, end, index = 0, len(self.interpolated_loudness_buffer) - 1, None
        while start <= end:
            mid = start + (end - start) // 2
            lower_bound, upper_bound, _ = self.interpolated_loudness_buffer[mid]
            if lower_bound <= pos <= upper_bound:
                index = mid
                break
            if pos < lower_bound:
                end = mid - 1
            if pos > upper_bound:
                start = mid + 1

        to_return = None
        if index is not None:
            to_return = (
                self.interpolated_loudness_buffer[index][-1],
                self.interpolated_pitch_buffer[index][-1],
            )
        self.buffer_lock.release()
        return to_return

    def _load_track_data(self, chunk_length=30):
        """Obtain track data from the Spotify API and run necessary analysis to generate data needed for visualization.

        Each call to this function analyzes the next chunk_length seconds of track data and produces the appropriate
        interpolated loudness and pitch functions. These interpolated functions are added to their
        corresponding buffers.

        Args:
            chunk_length (float): the number of seconds of track data to analyze.
        """
        # Extract the next chunk_length seconds of useful loudness and pitch data
        s_t, l, pitch_lists = [], [], []
        i = 0
        chunk_start = self.data_segments[0]["start"]
        while i < len(self.data_segments):
            s_t.append(self.data_segments[i]["start"])
            l.append(self.data_segments[i]["loudness_start"])
            pitch_lists.append(self.data_segments[i]["pitches"])

            # If we've analyzed chunk_length seconds of data, and there is more than 2 segments remaining, break
            if self.data_segments[i]["start"] > chunk_start + chunk_length and i < len(self.data_segments) - 1:
                break
            i += 1
        chunk_end = self.data_segments[i]["start"] if i < len(self.data_segments) else self.data_segments[-1]["start"]

        # Discard data segments that were just analyzed
        self.data_segments = self.data_segments[i:]

        # Perform data interpolation for loudness and pitch data
        start_times = np.array(s_t)
        loudnesses = np.array(l)
        interpolated_loudness_func = interp1d(start_times, loudnesses, kind='cubic', assume_sorted=True)
        interpolated_pitch_funcs = []
        for i in range(12):
            # Create a separate interpolated pitch function for each of the 12 pitch keys
            interpolated_pitch_funcs.append(
                interp1d(
                    start_times,
                    [pitch_list[i] if pitch_list[i] >= 0 else 0 for pitch_list in pitch_lists],
                    kind="cubic",
                    assume_sorted=True
                )
            )

        # Add interpolated functions and their bounds to buffers for consumption by visualization thread
        self.buffer_lock.acquire()
        self.interpolated_loudness_buffer.append((chunk_start, chunk_end, interpolated_loudness_func))
        self.interpolated_pitch_buffer.append((chunk_start, chunk_end, interpolated_pitch_funcs))

        # Print information about the data chunk load that was just performed
        title = "--------------------DATA LOAD REPORT--------------------\n"
        data_seg = "Data segments remaining: {}.\n".format(len(self.data_segments))
        loudness = "Interpolated loudness buffer size: {}.\n".format(len(self.interpolated_loudness_buffer))
        pitch = "Interpolated pitch buffer size: {}.\n".format(len(self.interpolated_pitch_buffer))
        closer = "--------------------------------------------------------"
        self.buffer_lock.release()
        text = title + data_seg + loudness + pitch + closer
        print(SpotifyVisualizer._make_text_effect(text, ["blue"]))

    @staticmethod
    def _make_text_effect(text, text_effects):
        """"Applies text effects to text and returns it.

        Supported text effects:
            "green", "red", "blue", "bold"

        Args:
            text (str): the text to apply effects to.
            text_effects (list): a list of str, each str representing an effect to apply to the text.

        Returns:
            text (str) with effects applied.
        """
        effects = {
            "green": "\033[92m",
            "red": "\033[91m",
            "blue": "\033[94m",
            "bold": "\033[1m"
        }
        end_code = "\033[0m"
        msg_with_fx = ""
        for effect in text_effects:
            msg_with_fx += effects[effect]
        msg_with_fx += text
        msg_with_fx += end_code * len(text_effects)
        return msg_with_fx

    def _push_visual_to_strip(self, loudness_func, pitch_funcs, pos):
        """Displays a visual on the LED strip based on the loudness and pitch data at current playback position.

        Args:
            loudness_func (interp1d): interpolated loudness function.
            pitch_funcs (list): a list of interpolated pitch functions (one pitch function for each major musical key).
            pos (float): the current playback position (offset into the track in seconds).
        """
        self.visualizer.visualize(loudness_func, pitch_funcs, pos)

    def _reset(self):
        """Reset certain attributes to prepare to visualize a new track.
        """
        self.data_segments = []
        self.interpolated_loudness_buffer = []
        self.interpolated_pitch_buffer = []
        self.is_playing = True
        self.playback_pos = 0
        self.song_ended = False
        self.track = None
        self.track_duration = None
        self.track_id = None
        self.visualizer.reset()

    def _reset_track(self):
        """Pauses track and seeks to beginning.
        """
        text = "Starting track from beginning."
        print(SpotifyVisualizer._make_text_effect(text, ["green"]))
        if self.sp_gen.current_playback()["is_playing"]:
            self.sp_gen.pause_playback()
        self.sp_gen.seek_track(0)

    def _visualize(self, sample_rate=0.03):
        """Starts playback on Spotify user's account (if paused) and visualizes the current track.

        Args:
            sample_rate (float): how long to wait (in seconds) between each sample.
        """
        pos = self.playback_pos
        loudness_func,pitch_funcs = None, None

        try:
            if not self.sp_vis.current_playback()["is_playing"]:
                self.sp_vis.start_playback()
                self.is_playing = True
        except:
            pass

        # Visualize until end of track
        while pos <= self.track_duration:
            start = time.perf_counter()
            if self.song_ended:
                text = "Killing visualization thread."
                print(SpotifyVisualizer._make_text_effect(text, ["red", "bold"]))
                exit(0)
            path = 0
            try:
                if self.is_playing and loudness_func and pitch_funcs:
                    path = 1
                    pos = self.playback_pos
                    self._push_visual_to_strip(loudness_func, pitch_funcs, pos)
                elif not loudness_func or not pitch_funcs:
                    path = 2
                    funcs = self._get_buffers_for_pos(pos)
                    loudness_func, pitch_funcs = funcs if funcs else (None, None)
                    self.loading_animator.animate() # play one frame of animation
                else:
                    path = 3
                    self.loading_animator.animate() # play one frame of animation
            # If pitch or loudness value out of range, find the interpolated functions for the current position
            except ValueError as err:
                text = "Caught ValueError: {}\nSearching for interpolated funcs for current position...".format(err)
                print(SpotifyVisualizer._make_text_effect(text, ["red", "bold"]))
                print(SpotifyVisualizer._make_text_effect(str(path), ['blue', 'bold']))
                funcs = self._get_buffers_for_pos(pos)
                if funcs:
                    loudness_func, pitch_funcs = funcs
                else:
                    self.loading_animator.animate()
            # Unexpected error...retry
            except Exception as e:
                text = f"Unexpected error in visualization thread: {e} \nRetrying..."
                print(SpotifyVisualizer._make_text_effect(text, ["red", "bold"]))

            self.pos_lock.acquire()
            self.playback_pos += sample_rate
            self.pos_lock.release()
            end = time.perf_counter()

            # Account for time used to create visualization
            diff = sample_rate - (end - start)
            time.sleep(diff if diff > 0 else 0)
