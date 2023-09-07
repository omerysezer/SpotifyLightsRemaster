from src.Controller.settings_handler import SettingsHandler
from src.SpotifyLights.light_manager import manage
from src.Controller.rest_api import API
from src.Animations.animation_controller import AnimationController
import threading
from queue import Queue
import json
from src.led_strips.led_strip import LED_STRIP
import time
from src.Controller.spotify_login_handler import user_is_logged_in, get_auth_manager
class Controller:
    def __init__(self):
        self.settings_handler = SettingsHandler("./src/Files/settings.json")
        self.settings_lock = threading.Lock()

        self.api_communicaton_queue = Queue()
        self.api_kill_sentinel = object()
        self.api = API(self.api_communicaton_queue, self.api_kill_sentinel, self.settings_handler, self.settings_lock)
        self.api_thread = None

        self.spotify_lights_thread = None
        self.controller_to_lights_queue = Queue() # a queue so the controller can pass messages to spotify lights manager thread
        self.light_to_controller_queue = Queue() # a queue so spotify lights manager thread can pass messages to controller
        self.spotify_lights_kill_sentinel = object()
        self.spotify_lights_encounterd_error = False

        self.animation_controller = None
        self.animation_thread = None
        self.controller_to_animation_queue = Queue()
        self.animation_to_controller_queue = Queue()
        self.animation_kill_sentinel = object()

        self.current_command = None

        led_strip_type = self.settings_handler.get_strip_type()
        led_count = self.settings_handler.get_led_count()
        self.led_strip = None if led_strip_type is None else LED_STRIP(led_count, led_strip_type)        
        
    def run(self):
        self.api_thread = threading.Thread(target=self.api.run, name="rest_api_thread")
        self.api_thread.start()
        
        while True:
            if not self.api_communicaton_queue.empty():
                message = self.api_communicaton_queue.get()
                if 'BRIGHTNESS' in message:
                    self.led_strip.set_brightness(message['BRIGHTNESS'])
                if 'SPOTIFY_COLORS' in message and self._spotify_lights_are_running():
                    self.controller_to_lights_queue.put({'SPOTIFY_COLORS': message['SPOTIFY_COLORS']})
                    self.controller_to_lights_queue.join()
                if 'COMMAND' in message:
                    command = message['COMMAND']
                    if command == 'LIGHTS_OFF':
                        if self._spotify_lights_are_running():
                            self._kill_spotify_lights()
                        if self._animation_is_running():
                            self._kill_animation_thread()
                    elif command == 'SPOTIFY_LIGHTS_ON':
                        if self._animation_is_running():
                            self._kill_animation_thread()
                        if not self._spotify_lights_are_running():
                            self._start_spotify_lights()

                        self.spotify_lights_encounterd_error = False
                    elif command == 'ANIMATION_LIGHTS_ON':
                        if self._spotify_lights_are_running():
                            self._kill_spotify_lights()
                        if not self._animation_is_running():
                            self._start_animation_thread()
                    self.current_command = command
                if 'LOGGED_OUT' in message:
                    self._kill_spotify_lights()
                if 'AUTH_HANDLER' in message:
                    self._kill_spotify_lights()
                    self._start_spotify_lights()
                if 'ANIMATION_SETTINGS_UPDATED' in message:
                    self._kill_animation_thread()
                    self.settings_lock.acquire()
                    default_behaviour = self.settings_handler.get_default_behaviour()
                    self.settings_lock.release()

                    if (default_behaviour == "ANIMATION_LIGHTS_ON" and not self.current_command) or self.current_command == "ANIMATION_LIGHTS_ON":
                        self._start_animation_thread()

                if 'UPDATE_STRIP_TYPE' in message:
                    strip_details = message['UPDATE_STRIP_TYPE']
                    num_led = strip_details['NUM_LED']
                    strip_type = strip_details['STRIP_TYPE']
                    self._kill_spotify_lights()
                    self._kill_animation_thread()
                    self.led_strip = LED_STRIP(num_led, strip_type)
                if 'NEXT_ANIMATION' in message:
                    if self._animation_is_running():
                        self.controller_to_animation_queue.put('NEXT_ANIMATION')
                        self.controller_to_animation_queue.join()
                if 'PREV_ANIMATION' in message:
                    if self._animation_is_running():
                        self.controller_to_animation_queue.put('PREV_ANIMATION')
                        self.controller_to_animation_queue.join()
                if 'GET_ANIMATION_IDX' in message:
                    idx_holder = {'GET_ANIMATION_IDX': None}
                    self.controller_to_animation_queue.put(idx_holder)
                    self.controller_to_animation_queue.join()
                    idx = idx_holder['GET_ANIMATION_IDX']
                    message['GET_ANIMATION_IDX'] = idx

                self.api_communicaton_queue.task_done()
            
            if not self.light_to_controller_queue.empty():
                message = self.light_to_controller_queue.get()
                if message == 'USER NOT LOGGED IN':
                    self._kill_spotify_lights()
                
                if message == 'TIMED_OUT':
                    self._kill_spotify_lights()
                    self.spotify_lights_encounterd_error = True
                    if self.current_command == 'SPOTIFY_LIGHTS_ON':
                        self.current_command = None
                    
                    self.api.notify_spotify_lights_timed_out()

            authenticated = user_is_logged_in()
            if not authenticated:
                self._kill_spotify_lights()

            # default behaviour should only be triggered if there is no overriding command in self.current_command
            if not self.current_command and self.led_strip:
                self.settings_lock.acquire()
                default_behaviour = self.settings_handler.get_default_behaviour() 
                self.settings_lock.release()

                if default_behaviour == "SPOTIFY_LIGHTS_ON" and not self._spotify_lights_are_running() and authenticated:
                    if not self.spotify_lights_encounterd_error:
                        self._kill_animation_thread()
                        self._start_spotify_lights()
                elif default_behaviour == "ANIMATION_LIGHTS_ON" and not self._animation_is_running():
                    self._kill_spotify_lights()
                    
                    # create thread only if there are files to show
                    self.settings_lock.acquire()
                    animation_list = self.settings_handler.get_animations()
                    self.settings_lock.release()

                    if animation_list:
                        self._start_animation_thread()
                elif default_behaviour == "LIGHTS_OFF":
                    self._kill_spotify_lights()
                    self._kill_animation_thread()
            elif self.current_command and self.led_strip:
                if self.current_command == "SPOTIFY_LIGHTS_ON" and not self._spotify_lights_are_running() and authenticated:
                     if not self.spotify_lights_encounterd_error:
                        self._kill_animation_thread()
                        self._start_spotify_lights()
                elif self.current_command == "ANIMATION_LIGHTS_ON" and not self._animation_is_running():
                    self._kill_spotify_lights()
                    
                    # create thread only if there are files to show
                    self.settings_lock.acquire()
                    animation_list = self.settings_handler.get_animations()
                    self.settings_lock.release()

                    if animation_list:
                        self._start_animation_thread()
                elif self.current_command == "LIGHTS_OFF":
                    self._kill_spotify_lights()
                    self._kill_animation_thread()
                    
            time.sleep(.1)

    def _start_spotify_lights(self):
        if self._spotify_lights_are_running() or not self.led_strip:
            return
        
        self.settings_lock.acquire()
        primary_color = self.settings_handler.get_primary_color()
        secondary_color = self.settings_handler.get_secondary_color()
        self.settings_lock.release()

        auth_manager = get_auth_manager()
        self.controller_to_lights_queue = Queue() # a queue so the controller can pass messages to spotify lights manager thread
        self.light_to_controller_queue = Queue() # a queue so spotify lights manager thread can pass messages to controller
        self.spotify_lights_thread = threading.Thread(target=manage, name="spotify_lights_thread", args=(False, primary_color, secondary_color, auth_manager,
                                                                                                  self.controller_to_lights_queue, self.light_to_controller_queue, 
                                                                                                  self.spotify_lights_kill_sentinel, self.led_strip))
        self.spotify_lights_thread.start()

    def _kill_spotify_lights(self):
        if not self._spotify_lights_are_running():
            return

        self.controller_to_lights_queue.put(self.spotify_lights_kill_sentinel)
        self.controller_to_lights_queue.join() # wait for spotify lights to mark command as completed
        self.spotify_lights_thread.join() 

        self.controller_to_lights_queue = Queue() # clear the queues if there were any messages waiting
        self.light_to_controller_queue = Queue()

    def _spotify_lights_are_running(self):
        return self.spotify_lights_thread and self.spotify_lights_thread.is_alive()
            
    def _start_animation_thread(self):
        if self._animation_is_running() or not self.led_strip:
            return
        
        self.settings_lock.acquire()
        animation_list = self.settings_handler.get_animations()
        animation_duration = self.settings_handler.get_animation_duration()
        self.settings_lock.release()
        
        self.controller_to_animation_queue = Queue()
        self.animation_to_controller_queue = Queue()
        self.animation_controller = AnimationController(animation_list, animation_duration, self.controller_to_animation_queue, 
                                                        self.animation_to_controller_queue, self.animation_kill_sentinel, self.led_strip)
        self.animation_thread = threading.Thread(target=self.animation_controller.run, name="animation_thread")
        self.animation_thread.start()
        
    def _kill_animation_thread(self):
        if not self._animation_is_running():
            return

        self.controller_to_animation_queue.put(self.animation_kill_sentinel)
        self.controller_to_animation_queue.join()
        self.animation_thread.join()

        if self._animation_is_running():
            raise Exception("Could Not Kill Animation Thread")
        
        self.animation_to_controller_queue = Queue()
        self.controller_to_animation_queue = Queue()
        
    def _animation_is_running(self):
        return self.animation_thread and self.animation_thread.is_alive() 
