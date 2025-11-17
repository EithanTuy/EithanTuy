# seed.py
# handles seed strings and converting them to deterministic integers.

import random
import hashlib

class SeedRNG:
    # wrapper around python random to allow deterministic per-run state
    # all comments are lowercase.

    def __init__(self, seed_string):
        if seed_string is None or seed_string.strip() == "":
            # random seed if none supplied
            seed_string = str(random.randint(1, 10**12))

        self.seed_string = seed_string

        # convert seed string → 64 bit int using sha256 for consistency
        digest = hashlib.sha256(seed_string.encode()).hexdigest()
        seed_int = int(digest[:16], 16)

        self.rng = random.Random(seed_int)

    def randint(self, a, b):
        return self.rng.randint(a, b)

    def random(self):
        return self.rng.random()

    def choice(self, seq):
        return self.rng.choice(seq)

    def shuffle(self, lst):
        self.rng.shuffle(lst)

    def uniform(self, a, b):
        return self.rng.uniform(a, b)
