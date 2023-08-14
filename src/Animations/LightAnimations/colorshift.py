from time import time
from random import randint

class colorshift:
    def __init__(self, strip, num_led):
        self.strip = strip
        self.num_led = num_led

        self.curr_color = (randint(0, 255), randint(0, 255), randint(0, 255))
        self.next_color = (randint(0, 255), randint(0, 255), randint(0, 255))
        
        self.time_since_last_frame = float('-inf')
        self.time_per_frame_ms = 15

    def run(self):
        if time() * 1000 - self.time_since_last_frame >= self.time_per_frame_ms:
            if self.curr_color == self.next_color:
                self.next_color = (randint(0, 255), randint(0, 255), randint(0, 255))

            curr_r, curr_g, curr_b = self.curr_color
            next_r, next_g, next_b = self.next_color

            if curr_r != next_r:
                curr_r = curr_r + 1 if curr_r < next_r else curr_r - 1
            if curr_g != next_g:
                curr_g = curr_g + 1 if curr_g < next_g else curr_g - 1
            if curr_b != next_b:
                curr_b = curr_b + 1 if curr_b < next_b else curr_b - 1
            
            self.curr_color = curr_r, curr_g, curr_b
            for i in range(self.num_led):
                self.strip.set_pixel(i, *self.curr_color)
            
            self.strip.show()
            self.time_since_last_frame = time() * 1000