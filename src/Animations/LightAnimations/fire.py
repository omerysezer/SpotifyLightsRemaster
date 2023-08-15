import random
from time import time

class fire:
    def __init__(self, strip, num_led):
        self.strip = strip
        self.num_led = num_led

        self.frame_delay_ms = random.randint(50, 150)
        self.last_frame_start_ms = float('-inf')

        self.fire_colors = [
            {'color': (255, 150, 0), 'chance': .4},  # Yellow-Orange
            {'color': (255, 75, 0), 'chance': .4},    # Orange-Red
            {'color': (255, 0, 0), 'chance': .15},     # Red
            {'color': (150, 0, 0), 'chance': .05},     # Dim Red
        ]

    def run(self):
        if time() * 1000 - self.last_frame_start_ms >= self.frame_delay_ms:
            pixel_indices = list(range(0, self.num_led))
            random.shuffle(pixel_indices)
            for c in self.fire_colors:
                color = c['color']
                chance = c['chance']
                for i in range(int(self.num_led * chance)):
                    new_color = tuple([min(255, int(random.randint(75, 100) / 100 * channel)) for channel in color])
                    self.strip.set_pixel(pixel_indices[i], *new_color)

            self.strip.show()
            self.last_frame_start_ms = time() * 1000
            self.frame_delay_ms = random.choice(range(50, 150))
