from time import time
import random

class christmas:
    def __init__(self, strip, num_led):
        self.strip = strip
        self.num_led = num_led

        self.ms_between_frames = 500
        self.ms_since_last_frame = float('-inf')

        self.colors = [
            (255, 0, 0),    # Red
            (0, 220, 0),    # Green
            (255, 255, 255), # Dim White
            (255, 255, 0), # yellow
            (0, 0, 255) # blue
        ]
        

    def run(self):
        if time() * 1000 - self.ms_since_last_frame >= self.ms_between_frames:
            weighted_random_colors = random.choices(self.colors, weights=(0.2, 0.4, 0.1, 0.1, 0.1), k=self.num_led)
            for i, color in enumerate(weighted_random_colors): self.strip.set_pixel(i, *color)

            self.strip.show()
            self.ms_since_last_frame = time() * 1000