from apa102_pi.driver import apa102

class LED_STRIP(apa102.APA102):
    def fill(self, start, end, r, g, b, brightness):
        for i in range(start, end):
            self.set_pixel(i, r, g, b, brightness)