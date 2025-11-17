# timer.py
# speedrun timer that pauses correctly and supports splits.
# all comments lowercase.

class RunTimer:
    def __init__(self):
        self.time = 0.0
        self.running = False

        # split history: each floor completion timestamp
        self.splits = []

    def start(self):
        # begin or resume timer
        self.running = True

    def stop(self):
        # pause timer
        self.running = False

    def reset(self):
        self.time = 0.0
        self.running = False
        self.splits = []

    def update(self, dt):
        # only counts when running
        if self.running:
            self.time += dt

    def split(self):
        # record floor completion time
        self.splits.append(self.time)

    def get_time(self):
        return self.time
