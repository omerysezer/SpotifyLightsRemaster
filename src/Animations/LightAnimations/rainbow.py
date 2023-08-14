from time import time

class rainbow:
    def __init__(self, strip, num_led):
        self.strip = strip
        self.num_led = num_led

        self.last_frame_start_time_ms = float('-inf')
        self.frame_duration_ms = 100
    
        self.rainbow_colors = [
            (148, 0, 211),   # Violet
            (75, 0, 130),    # Indigo
            (0, 0, 255),     # Blue
            (0, 255, 0),     # Green
            (255, 255, 0),   # Yellow
            (255, 127, 0),   # Orange
            (255, 0, 0)      # Red
        ]

        self.num_pixels_per_color = self.num_led // len(self.rainbow_colors)
        self.offset = 0

    def run(self):
        curr_time_ms = time() * 1000
        if curr_time_ms - self.last_frame_start_time_ms >= self.frame_duration_ms:
            for i in range(self.num_led):
                self.strip.set_pixel((i + self.offset) % self.num_led, *self.rainbow_colors[(i // self.num_pixels_per_color) % len(self.rainbow_colors)])
            
            self.offset = (self.offset + 1) % self.num_led
            self.strip.show()
            self.last_frame_start_time_ms = time() * 1000