import board
import adafruit_dotstar
import neopixel
import threading
class LED_STRIP:
    def __init__(self, num_led=0, strip_type='dotstar', brightness=1.0):
        '''
            parameters:
                num_led (int): the number of pixels on the led strip
                strip_type (["neopixel", "dotstar"]): The type of led strip being used
        '''
        if strip_type not in ["neopixel", "dotstar"]:
            raise Exception(f"Unsupported strip type: '{strip_type}'. Strip must be of type either 'neopixel' or 'dotstar'.")

        if strip_type == "neopixel":
            self._strip = neopixel.NeoPixel(pin=board.D18, n=num_led, brightness=brightness, auto_write=False, pixel_order=neopixel.GRB)
        else:
            # adafruit_dotstar.BGR is used because BGR and RGB are backwards for some reason
            self._strip = adafruit_dotstar.DotStar(clock=board.D11, data=board.D10, n=num_led, brightness=brightness, auto_write=False, pixel_order=adafruit_dotstar.BGR, baudrate=8000000)

        self.num_led = num_led
        self.brightness = brightness
        self.light_lock = threading.Lock()
        self._pixel_values = [(0,0,0)] * num_led

        # reset lights to black before beginning
        for i in range(self.num_led):
            self._strip[i] = (0, 0, 0)
        self._strip.show()

    def fill(self, start, end, r, g, b):
        # doesnt need to have lock because it calls set_pixel which acquires the lock
        for i in range(start, end):
            self.set_pixel(i, r, g, b)

    def fill_all(self, r, g, b):
        # doesnt need to have lock because self.fill calls set_pixel which acquires the lock
        self.fill(0, self.num_led, r, g, b)

    def set_pixel(self, i, r, g, b):
        # we keep light brightness at 100% and adjust pixel values ourselves
        # changing brightness is expensive for the library
        self.light_lock.acquire()
        self._pixel_values[i] = (r,g,b)
        self._strip[i] = tuple([round(channel * self.brightness) for channel in (r,g,b)])
        self.light_lock.release()

    def set_brightness(self, brightness):
        '''
        Takes a brightnes value from [0, 100]
        '''
        self.light_lock.acquire()
        self.brightness = brightness/100
        self.light_lock.release()
        for i in range(self.num_led):
           self.set_pixel(i, *self._pixel_values[i])
        self.show()

    def show(self):
        self.light_lock.acquire()
        self._strip.show()
        self.light_lock.release()

    def get_pixel_count(self):
        self.light_lock.acquire()
        num_led = self.num_led
        self.light_lock.release()
        return self.num_led

    def reset(self):
        self.fill_all(0, 0, 0)
        self.show()
