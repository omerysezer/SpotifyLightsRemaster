from importlib import import_module

class AnimationController:
    def __init__(self, animation_names, animation_runtime, controller_to_animation_q, animation_to_controller_q, kill_sentinel):
        self.animation_time = animation_runtime

        self.animations = []
        self.animation_loads_failed = []
        for animation_name in animation_names:
            try:   
                animation = getattr(import_module(f"src.Animations.LightAnimations.{animation_name}", package="."), animation_name)
                self.animations.append(animation)
            except Exception as e:
                self.animation_loads_failed.append(animation_name)
                print(e)
        
    def get_classes_which_failed_to_load(self):
        return self.animation_loads_failed
    
    def run(self):
        pass