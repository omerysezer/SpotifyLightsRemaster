import board
import adafruit_dotstar
import neopixel
import threading
class LED_STRIP:
    def __init__(self, num_led, strip_type):
        '''
            parameters:
                num_led (int): the number of pixels on the led strip
                strip_type (["neopixel", "dotstar"]): The type of led strip being used
        '''

        if strip_type not in ["neopixel", "dotstar"]:
            raise Exception(f"Unsupported strip type: '{strip_type}'. Strip must be of type either 'neopixel' or 'dotstar'.")
        
        self._strip = None
        if strip_type == "neopixel":
            self._strip = neopixel.NeoPixel(pin=board.D10, n=num_led, brightness=1.0, auto_write=False, pixel_order="PRGB")
        else:
            # adafruit_dotstar.BGR is used because BGR and RGB are backwards for some reason
            self._strip = adafruit_dotstar.DotStar(clock=board.D11, data=board.D10, n=175, brightness=1.0, auto_write=False, pixel_order=adafruit_dotstar.BGR, baudrate=8000000)
        
        self.num_led = num_led
        self.brightness = 1.0
        self.light_lock = threading.Lock()

    def fill(self, start, end, r, g, b):
        for i in range(start, end):
            self.set_pixel(i, r, g, b)

    def fill_all(self, r, g, b):
        self._strip.fill((r, g, b))

    def set_pixel(self, i, r, g, b):
        rgb = (int(r * self.brightness), int(g * self.brightness), int(b * self.brightness))
        try:
            self._strip[i] = rgb
        except:
            print(i, rgb)

    def set_brightness(self, brightness):
        '''
        Takes a brightnes value from [0, 100]
        '''
        self._strip.brightness = brightness/100

    def show(self):
        self._strip.show()
    
    def get_pixel_count(self):
        return self.num_led