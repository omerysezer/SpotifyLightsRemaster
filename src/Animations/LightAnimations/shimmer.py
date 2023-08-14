from time import time
import random

class shimmer:
    def __init__(self, strip, num_led):
        self.strip = strip
        self.num_led = num_led

        self.shimmering = False
        self.time_between_shimmers_ms = 1500
        self.time_of_last_shimmer = float('-inf')

        self.time_since_shimmer_progressed = float('-inf')
        self.shimmer_frame_time_ms = 10

        self.time_between_bg_updates_ms = 100
        self.time_of_last_bg_update = float('-inf')

        if num_led % 2 == 0:
            self.left_shimmer_pos = (num_led / 2) - 1
            self.right_shimmer_pos = num_led / 2
        else:
            self.left_shimmer_pos, self.right_shimmer_pos = self.num_led // 2, self.num_led // 2

        self.bg_color = (75, 0, 130) # purple

        self.pixel_vals = [self.bg_color] * self.num_led

    def set_bg(self):
        for i in range(self.num_led):
            brightness_shift = random.uniform(.75, 1.25)
            r, g, b = self.pixel_vals[i]

            r = min(int(r * brightness_shift), 255)
            g = min(int(g * brightness_shift), 255)
            b = min(int(b * brightness_shift), 255)

            self.strip.set_pixel(i, r, g, b)
        self.strip.show()

    def run(self):
        curr_time_ms = time() * 1000
        if curr_time_ms - self.time_of_last_bg_update >= self.time_between_bg_updates_ms:
            self.set_bg()
            self.time_of_last_bg_update = curr_time_ms    
        
            