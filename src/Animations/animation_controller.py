from importlib import import_module
import os
from time import time, sleep

class AnimationController:
    def __init__(self, animation_names, animation_runtime, controller_to_animation_queue, animation_to_controller_queue, kill_sentinel):
        self.controller_to_animation_queue = controller_to_animation_queue
        self.animation_to_controller_queue = animation_to_controller_queue
        self.kill_sentinel = kill_sentinel

        self.animation_time = animation_runtime

        # if no set of animations are specified, add all possible animations to list
        if not animation_names:
            all_animation_files = [file[:-3] for file in os.listdir('./src/Animations/LightAnimations/') if file.endswith('.py')]
            animation_names = all_animation_files

        self.animations = []
        self.animation_loads_failed = []
        for animation_name in animation_names:
            try:   
                animation = getattr(import_module(f"src.Animations.LightAnimations.{animation_name}", package="."), animation_name)
                self.animations.append(animation(None))
            except Exception as e:
                self.animation_loads_failed.append(animation_name)
                print(e)
        
    def get_classes_which_failed_to_load(self):
        return self.animation_loads_failed
    
    def run(self):
        animation_index = 0
        time_of_animation_start = None
        while True:
            if not self.controller_to_animation_queue.empty():
                message = self.controller_to_animation_queue.get()

                if message == self.kill_sentinel:
                    return
            
            # move on to the next animation if time for current animation is up or we have not started any animation yet
            current_time = int(time() * 1000) 
            if not time_of_animation_start or current_time - time_of_animation_start > self.animation_time:
                time_of_animation_start = current_time
                animation_index = (animation_index + 1) % len(self.animations)
            
            self.animations[animation_index].run()
            sleep(.01)