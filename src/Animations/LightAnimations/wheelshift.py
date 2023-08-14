from time import time
from random import randint

class wheelshift:
    def __init__(self, strip, num_led):
        self.strip = strip
        self.num_led = num_led

        self.wheel_rotate_frame_time_ms = 100
        self.time_of_last_rotation = float('-inf')

        self.color_shift_frame_time_ms = 5
        self.time_of_last_shift = float('-inf')

        self.num_colors = 7
        self.curr_colors = [self.get_random_color() for _ in range(self.num_colors)]
        self.next_colors = [self.get_random_color() for _ in range(self.num_colors)]
        
        self.num_pixels_per_color = self.num_led // self.num_colors
        self.offset = 0

    def get_random_color(self):
        return (randint(0, 255), randint(0, 255), randint(0, 255))

    def run(self):
        if time() * 1000 - self.time_of_last_rotation >= self.wheel_rotate_frame_time_ms:
            for i in range(self.num_led):
                self.strip.set_pixel((i + self.offset) % self.num_led, *self.curr_colors[(i // self.num_pixels_per_color) % len(self.curr_colors)])
            
            self.offset = (self.offset + 1) % self.num_led
            self.strip.show()
            self.time_of_last_rotation = time() * 1000
        
        if time() * 1000 - self.time_of_last_shift >= self.color_shift_frame_time_ms:
            for i in range(len(self.curr_colors)):
                if self.curr_colors[i] == self.next_colors[i]:
                    new_color = []
                    for channel in self.curr_colors[i]:
                        new_channel_increased = randint(min(int(channel * 1.5), 255), 255)
                        new_channel_decreased = randint(0, int(channel * .5))

                        if abs(channel - new_channel_increased) > abs(channel - new_channel_decreased):
                            new_channel = new_channel_increased
                        else:
                            new_channel = new_channel_decreased
                        new_color.append(new_channel)
                    self.next_colors[i] = tuple(new_color)

                curr_r, curr_g, curr_b = self.curr_colors[i]
                next_r, next_g, next_b = self.next_colors[i]

                if curr_r != next_r:
                    curr_r = curr_r + 1 if curr_r < next_r else curr_r - 1
                if curr_g != next_g:
                    curr_g = curr_g + 1 if curr_g < next_g else curr_g - 1
                if curr_b != next_b:
                    curr_b = curr_b + 1 if curr_b < next_b else curr_b - 1
                
                self.curr_colors[i] = curr_r, curr_g, curr_b
                for i in range(self.num_led):
                    self.strip.set_pixel((i + self.offset) % self.num_led, *self.curr_colors[(i // self.num_pixels_per_color) % len(self.curr_colors)])
                
            self.strip.show()
            self.time_of_last_shift = time() * 1000