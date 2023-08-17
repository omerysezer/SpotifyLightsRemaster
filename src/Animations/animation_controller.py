from importlib import import_module
import os
from time import time, sleep

class AnimationController:
    def __init__(self, animation_names, animation_runtime, controller_to_animation_queue, animation_to_controller_queue, kill_sentinel, led_strip):
        self.controller_to_animation_queue = controller_to_animation_queue
        self.animation_to_controller_queue = animation_to_controller_queue
        self.kill_sentinel = kill_sentinel

        self.lights = led_strip
        self.num_pixels = self.lights.get_pixel_count()

        self.animation_time_ms = animation_runtime * 1000

        self.animations = []
        self.animation_loads_failed = []
        self.animation_idx = 0
        
        animation_names = animation_names or []
        for animation_name in animation_names:
            try:   
                animation = getattr(import_module(f"src.Animations.LightAnimations.{animation_name}", package="."), animation_name)
                self.animations.append(animation(self.lights, self.num_pixels))
            except Exception as e:
                self.animation_loads_failed.append(animation_name)
                print(e)

    def get_classes_which_failed_to_load(self):
        return self.animation_loads_failed
    
    def run(self):
        time_of_animation_start_ms = float('-inf')
        while True and self.animations:
            if not self.controller_to_animation_queue.empty():
                message = self.controller_to_animation_queue.get()

                if message == self.kill_sentinel:
                    self.lights.fill_all(0, 0, 0)
                    self.lights.show()
                    self.controller_to_animation_queue.task_done()
                    return
                if message == 'NEXT_ANIMATION':
                    self.animation_idx = (self.animation_idx + 1) % len(self.animations)
                    self.controller_to_animation_queue.task_done()
                if message == 'PREV_ANIMATION':
                    self.animation_idx = (self.animation_idx - 1) % len(self.animations)
                    self.controller_to_animation_queue.task_done()
                if 'GET_ANIMATION_IDX' in message:
                    message['GET_ANIMATION_IDX'] = self.animation_idx
                    self.controller_to_animation_queue.task_done()

            # move on to the next animation if time for current animation is up or we have not started any animation yet
            current_time_ms = int(time() * 1000) 
            if current_time_ms - time_of_animation_start_ms > self.animation_time_ms:
                time_of_animation_start_ms = current_time_ms
                self.animation_idx = (self.animation_idx + 1) % len(self.animations)
            
            self.animations[self.animation_idx].run()
            sleep(.005)