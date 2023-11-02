from generators import *

class Board():
    def __init__(self, w, h, generator: BaseGenerator) -> None:
        self.width = w
        self.height = h
        allgoals = generator.get(w*h)

    def get_dict(self, base:dict={}) -> dict:
        base.update({"type": str(type(self)),
                     "width": self.width,
                     "height": self.height})
        return base