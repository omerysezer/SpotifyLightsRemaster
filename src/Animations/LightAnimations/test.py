from time import time

class test:
    def __init__(self, strip):
        self.strip = strip
        self.last_call_time = None
        self.c = 0
    def run(self):
        current_time = int(time() * 1000)

        if self.last_call_time is None or current_time - self.last_call_time > 1000: 
            self.last_call_time = current_time
            print(f"test{self.c}")
            self.c += 1
