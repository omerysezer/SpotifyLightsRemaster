from time import time
import random

class RainbowWaterFall:
    def __init__(self, strip, num_led):
        self.strip = strip
        self.num_led = num_led

        self.rainbow_colors = [
            (148, 0, 211),   # Violet
            (75, 0, 130),    # Indigo
            (0, 0, 255),     # Blue
            (0, 255, 0),     # Green
            (255, 255, 0),   # Yellow
            (255, 127, 0),   # Orange
            (255, 0, 0)      # Red
        ]

        self.falling_droplets = []

        self.ms_since_droplet_left_side = float('-inf')
        self.ms_since_droplet_right_side = float('-inf')
        self.ms_between_droplets_right_side = 100
        self.ms_between_droplets_left_side = 100

        self.ms_between_frames_falling_droplets = 10

        self.ms_since_last_rotation = float('-inf')
        self.ms_between_rotation_frames = 50

        self.rainbow_left_boundary, self.rainbow_right_boundary = int(0.85 * num_led), int(0.15 * num_led)
        self.num_pixels_in_rotation = self.rainbow_left_boundary - self.rainbow_right_boundary
        self.rotation_offset = 0
        self.num_pixels_per_color = self.num_pixels_in_rotation // len(self.rainbow_colors)

        self.ms_between_shimmers = 100
        self.ms_since_last_shimmer = float('-inf')
        self.pixel_values = [(0, 0, 0)] * self.num_led

    def set_rotation(self):
        if time() * 1000 - self.ms_since_last_rotation >= self.ms_between_rotation_frames:
            for i in range(self.num_pixels_in_rotation):
                pixel_idx = (i + self.rotation_offset) % self.num_pixels_in_rotation + self.rainbow_right_boundary
                color = self.rainbow_colors[(i // self.num_pixels_per_color) % len(self.rainbow_colors)]
                self.pixel_values[pixel_idx] = color
                self.strip.set_pixel(pixel_idx, *color)
            
            self.rotation_offset = (self.rotation_offset + 1) % self.num_pixels_in_rotation
            self.ms_since_last_rotation = time() * 1000

    def set_shimmer(self):
        if time() * 1000 - self.ms_since_last_shimmer >= self.ms_between_shimmers:
            pixels_to_shift = random.sample(range(0, self.num_led), int(self.num_led * 0.5))
            for pixel_idx in pixels_to_shift:
                brightness_shift = min(random.uniform(0.8, 1.2 + 0.001), 1.25)
                r,g,b = self.pixel_values[pixel_idx] 
                self.strip.set_pixel(pixel_idx, min(int(r * brightness_shift), 255), min(int(g * brightness_shift), 255), min(int(b * brightness_shift), 255))
            
    def animate_droplets(self):
        if time() * 1000 - self.ms_since_droplet_left_side >= self.ms_between_droplets_left_side:
            self.falling_droplets.append({
                'color': self.pixel_values[self.rainbow_left_boundary - 1],
                'idx': self.rainbow_left_boundary,
                'ms_since_last_animation': float('-inf')
            })

            self.ms_since_droplet_left_side = time() * 1000
            self.ms_between_droplets_left_side = random.randint(250, 1500)

        if time() * 1000 - self.ms_since_droplet_right_side >= self.ms_between_droplets_right_side:
            self.falling_droplets.append({
                'color': self.pixel_values[self.rainbow_right_boundary],
                'idx': self.rainbow_right_boundary,
                'ms_since_last_animation': float('-inf')
            })

            self.ms_since_droplet_right_side = time() * 1000
            self.ms_between_droplets_right_side = random.randint(250, 1500)

        for droplet_idx in range(len(self.falling_droplets)):
            pixel = self.falling_droplets[droplet_idx]        
            color, pixel_idx, time_since_last_frame = pixel['color'], pixel['idx'], pixel['ms_since_last_animation']  
            
            if False or time() * 1000 - time_since_last_frame >= self.ms_between_frames_falling_droplets:
                self.pixel_values[pixel_idx] = (0, 0, 0)
                self.strip.set_pixel(pixel_idx, 0, 0, 0)

                pixel_idx = pixel_idx + 1 if pixel_idx >= self.rainbow_left_boundary else pixel_idx - 1
                self.falling_droplets[droplet_idx]['idx'] = pixel_idx

                if pixel_idx < 0 or pixel_idx >= self.num_led:
                    continue

                self.pixel_values[pixel_idx] = color
                self.strip.set_pixel(pixel_idx, *color)
                self.falling_droplets[droplet_idx]['ms_since_last_animation'] = time() * 1000

        self.falling_droplets = [droplet for droplet in self.falling_droplets if 0 <= droplet['idx'] < self.num_led]   

    def run(self):
        self.animate_droplets()
        self.set_rotation()
        # self.set_shimmer()
        self.strip.show()