import sys
import threading
import time

from src.SpotifyLights.Animations.LoadingAnimator import LoadingAnimator
from src.Files.credentials import AWS_ACCESS_KEY, AWS_SECRET_KEY, USER
from src.SpotifyLights.dynamodb_client import DynamoDBClient
from src.SpotifyLights.spotify_visualizer import SpotifyVisualizer
from src.SpotifyLights.Visualizations.LoudnessLengthEdgeFadeVisualizer import LoudnessLengthEdgeFadeVisualizer

import logging

# Set the logging level to WARNING (or higher) for the root logger
logging.basicConfig(level=logging.WARNING)

def _init_visualizer(dev_mode, n_pixels, base_color):
    if dev_mode:
        from src.led_strips.virtual_led_strip import VirtualLEDStrip
        visualization_device = VirtualLEDStrip()
    else:
        from src.led_strips.led_strip import LED_STRIP
        visualization_device = LED_STRIP(num_led=n_pixels, strip_type='dotstar')

    visualizer = LoudnessLengthEdgeFadeVisualizer(visualization_device, n_pixels, base_color)
    loading_animator = LoadingAnimator(visualization_device, n_pixels)
    return (visualizer, loading_animator)


def manage(dev_mode, initial_base_color, auth_manager, controller_to_lights_queue, lights_to_controller_queue, kill_sentinel):
    """ Lifecycle manager for the program

    In order to restart the lights remotely if an update is required, this level
    of abstraction separates the lifecycle of the lights from the visualization
    logic itself.

    Args:
        dev_mode (boolean): a flag denoting if the program is being run on the
    pi or a developer's machine.

    """
    base_color = None # We always want to update the lights on first start.
    visualizer_thread = None
    n_pixels = 175
    visualizer = None
    spotify_visualizer = None

    while True:
        if not controller_to_lights_queue.empty():
            command = controller_to_lights_queue.get()

            if command is kill_sentinel:
                if spotify_visualizer:
                    spotify_visualizer.terminate_visualizer()
                if visualizer_thread and visualizer_thread.is_alive():
                    visualizer_thread.join()

                controller_to_lights_queue.task_done()
                return

        new_base_color = initial_base_color
        if new_base_color != base_color:
            if visualizer:
                visualizer.set_primary_color(base_color)
            base_color = new_base_color

        if spotify_visualizer and visualizer_thread and not visualizer_thread.is_alive():
            spotify_visualizer.terminate_visualizer()
            while visualizer_thread.is_alive():
                print("Waiting for visualizer to terminate...")
                time.sleep(1)

        # If the animation has not been instantiated or the thread has
        # completed (i.e. we killed it), we need to reinstantiate and restart.
        if not visualizer_thread or not visualizer_thread.is_alive():
            visualizer, loading_animator = _init_visualizer(dev_mode, n_pixels, base_color)
            spotify_visualizer = SpotifyVisualizer(visualizer, loading_animator, auth_manager)
            visualizer_thread = threading.Thread(target=spotify_visualizer.launch_visualizer, name="visualizer_thread")
            visualizer_thread.start()

        time.sleep(1)

def activate():
    """ The outmost layer of the system.

    This is the entrypoint to the project and the outmost layer of the system.
    It is required because a GUI can only be run from the main thread, so any
    additional logic must be threadded to avoid blocking. The general structure
    now looks like this:

    - This script (Main thread)
        - manage() above
            - SpotifyVisualizer.launch_visualizer
                - data load
                - visualize
                - ...
    - GUI

    Args:
        developer_mode (boolean): determines if visualizer should be run from
        an actual lights strip or a virtual visualizer.
    """

    args = sys.argv
    if len(args) > 1:
        developer_mode = bool(args[1])
    else:
        developer_mode = False

    manager_thread = threading.Thread(target=manage, name="manager_thread", args=(developer_mode,))
    manager_thread.start()

    # If we are in developer mode, we need to use this main thread to start the
    # VirutalVisualizer GUI. Since VirtualLEDStrip is a singleton class, we
    # can just reinstantiate the VirtualLEDStrip
    if developer_mode:
        from src.led_strips.virtual_led_strip import VirtualLEDStrip
        VirtualLEDStrip().start_visualization()