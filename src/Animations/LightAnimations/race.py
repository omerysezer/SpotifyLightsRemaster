from time import time
import random

class race:
    def __init__(self, strip, num_led):
        self.strip = strip
        self.num_led = num_led

        self.midpoint = num_led // 2

        self.creating_new_race = True
        self.counting_down_new_race = False
        self.racing = False
        self.declaring_winner = False

        self.ms_since_last_count = float('-inf')
        self.ms_between_counts = 1000
        self.count = 2

        self.racer_1_color = None
        self.racer_1_speed = None
        self.racer_1_pos = None
        self.ms_since_update_1 = float('-inf')

        self.racer_2_color = None
        self.racer_2_speed = None
        self.racer_2_pos = None
        self.ms_since_update_2 = float('-inf')

        self.ms_between_race_frames = 5
        self.ms_since_last_frame = float('-inf')

        self.winner_declaration_start_time = None

    def random_color(self):
        # starts at 50 to prevent too dark / black colors
        return (random.randint(100, 255), random.randint(100, 255), random.randint(100, 255)) 

    def random_speed(self):
        return random.randint(5, 50)

    def create_new_race(self):
        self.racer_1_color = self.random_color()
        self.racer_2_color = self.random_color()
        
        self.racer_1_speed = self.random_speed()
        self.racer_2_speed = self.random_speed()

        if self.num_led % 2 == 0:
            self.racer_1_pos = (self.num_led // 2)  
            self.racer_2_pos = (self.num_led // 2) + 1  
        else: # if odd number of pixels racers start on either side of start pixel which is random
            self.racer_1_pos = (self.num_led // 2) - 1  
            self.racer_2_pos = (self.num_led // 2) + 1
            self.strip.set_pixel(self.num_led // 2, 0, 0, 0)

        self.strip.set_pixel(self.racer_1_pos, *self.racer_1_color)
        self.strip.set_pixel(self.racer_2_pos, *self.racer_2_color)
        self.strip.show()

        self.creating_new_race = False
        self.counting_down_new_race = True
    
    def count_down_race(self):
        count_colors = [(0, 255, 0), (255, 255, 0), (255, 0, 0)]
        if self.count >= 0 and time() * 1000 - self.ms_since_last_count >= self.ms_between_counts:
            color_to_show = count_colors[self.count]
            self.strip.fill_all(*color_to_show)
            self.strip.show()

            self.ms_since_last_count = time() * 1000
            self.count -= 1

        elif self.count < 0 and time() * 1000 - self.ms_since_last_count >= self.ms_between_counts:
            self.count = 2
            self.counting_down_new_race = False
            self.racing = True
            self.strip.fill_all(0, 0, 0)

    def race(self):

        if time() * 1000 - self.ms_since_update_1 >= self.racer_1_speed:
            self.racer_1_pos -= 1
            self.ms_since_update_1 = time() * 1000

        if time() * 1000 - self.ms_since_update_2 >= self.racer_2_speed:
            self.racer_2_pos += 1
            self.ms_since_update_2 = time() * 1000
        
        if self.racer_1_pos < 0 or self.racer_2_pos >= self.num_led:
            self.racing = False
            self.declaring_winner = True
            return

        if time() * 1000 - self.ms_since_last_frame >= self.ms_between_race_frames:
            self.strip.fill_all(0, 0, 0) # reset background

            for i in range(self.racer_1_pos, min(self.racer_1_pos + 10, self.num_led // 2)):
                self.strip.set_pixel(i, *self.racer_1_color)
            for i in range(self.racer_2_pos, max(self.racer_2_pos - 10, self.num_led // 2), -1):
                self.strip.set_pixel(i, *self.racer_2_color)

            self.strip.show()
            self.ms_since_last_frame = time() * 1000


    def declare_winner(self):
        if not self.winner_declaration_start_time:
            self.winner_declaration_start_time = time() * 1000

            if self.racer_1_pos < 0 and self.racer_2_pos >= self.num_led:
                for i in range(0, self.num_led // 2):
                    self.strip.set_pixel(i, *self.racer_1_color)
                for i in range(self.num_led // 2, self.num_led):
                    self.strip.set_pixel(i, *self.racer_2_color)
            elif self.racer_1_pos < 0:
                for i in range(self.num_led):
                    self.strip.set_pixel(i, *self.racer_1_color)
            elif self.racer_2_pos >= self.num_led:
                for i in range(self.num_led):
                    self.strip.set_pixel(i, *self.racer_2_color)

            self.strip.show()
        elif time() * 1000 - self.winner_declaration_start_time >= 1000:
            self.winner_declaration_start_time = None
            self.declaring_winner = False
            self.creating_new_race = True

    def run(self):
        if self.creating_new_race:
            self.create_new_race()
        elif self.counting_down_new_race:
            self.count_down_race()
        elif self.racing:
            self.race()
        elif self.declaring_winner:
            self.declare_winner()