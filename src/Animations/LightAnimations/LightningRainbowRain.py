import random
from time import time, sleep

class LightningRainbowRain:
    def __init__(self, strip, num_led):
        self.strip = strip
        self.num_led = num_led
    
        self.time_between_drops_ms = 100
        self.time_since_last_drop = None

        self.time_between_lightning = random.randint(250, 30000)
        self.time_since_last_lightning = time() * 1000
        self.lightning_active = False

        self.time_between_frames_ms = 25
        self.time_since_last_frame_ms = None

        self.active_pixels = {}
        self.inactive_pixels = []
        for i in range(self.num_led):
            self.inactive_pixels.append(i)

        for i in range(self.num_led):
            self.strip.set_pixel(i, 0, 0, 0)
        self.strip.show()

    def run(self):
        if not self.lightning_active:
            if not self.time_since_last_drop or time() * 1000 - self.time_since_last_drop >= self.time_between_drops_ms:
                pixel = random.choice(self.inactive_pixels)
                color = (random.randint(0, 255), random.randint(0, 255), random.randint(0, 255)) 
                self.strip.set_pixel(pixel, *color)
                self.active_pixels[pixel] = color
                self.inactive_pixels.remove(pixel)

                self.strip.show()
                self.time_between_drops_ms = random.randint(100, 1000)
                self.time_since_last_drop = time() * 1000

        if time() * 1000 - self.time_since_last_lightning >= self.time_between_lightning:
            pixels = list(self.active_pixels.keys())
            for pixel in pixels:
                self.active_pixels.pop(pixel)
                self.inactive_pixels.append(pixel)

            color = (random.randint(0, 255), random.randint(0, 255), random.randint(0, 255)) 
            for i in range(self.num_led):
                self.active_pixels[i] = color
                self.strip.set_pixel(i, *color)
            
            self.strip.show()
            self.time_since_last_lightning = time() * 1000
            self.lightning_active = True

        if not self.time_since_last_frame_ms or time() * 1000 - self.time_since_last_frame_ms >= self.time_between_frames_ms:
            if self.lightning_active:
                for pixel in self.active_pixels:
                    r, g, b = self.active_pixels[pixel]
                    r = int(r / 2)
                    g = int(g / 2)
                    b = int(b / 2)

                    self.active_pixels[pixel] = r, g, b
                    self.strip.set_pixel(pixel, r, g, b)

                pixel_colors = list(self.active_pixels.values())
                # if lightning is done fading remove all pixels from active list
                if not pixel_colors or pixel_colors[0] == (0, 0, 0):
                    self.lightning_active = False
                    drops_to_delete = []
                    for pixel in self.active_pixels:
                            drops_to_delete.append(pixel)
                            self.inactive_pixels.append(pixel)
                            self.strip.set_pixel(pixel, 0, 0, 0)
                    for pixel in drops_to_delete:
                        self.active_pixels.pop(pixel)

                self.time_between_lightning = random.randint(100, 10000)
                self.time_since_last_lightning = time() * 1000
            else:
                drops_to_delete = []
                for pixel in self.active_pixels:
                    r, g, b = self.active_pixels[pixel]
                    b = max(0, b - 5)

                    if b > 0:
                        self.active_pixels[pixel] = (r, g, b)
                        self.strip.set_pixel(pixel, r, g, b)
                    else:
                        drops_to_delete.append(pixel)
                        self.inactive_pixels.append(pixel)
                        self.strip.set_pixel(pixel, 0, 0, 0)
                for pixel in drops_to_delete:
                    self.active_pixels.pop(pixel)

                self.strip.show()
                self.time_since_last_frame_ms = time() * 1000
