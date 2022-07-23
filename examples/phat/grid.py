
class Box:
    def __init__(self, x1, y1, x2, y2):
        self.x1 = x1
        self.y1 = y1
        self.x2 = x2
        self.y2 = y2

    def __str__(self):
        return "({}, {}, {}, {})".format(self.x1, self.y1, self.x2, self.y2)

    def __repr__(self):
        return self.__str__()

    def top_left(self):
        return self.x1, self.y1

    def top_right(self):
        return self.x2, self.y1

    def bottom_left(self):
        return self.x1, self.y2

    def bottom_right(self):
        return self.x2, self.y2

    def center(self):
        return int((self.x1 + self.x2) / 2), int((self.y1 + self.y2) / 2)

    def width(self):
        return self.x2 - self.x1

    def height(self):
        return self.y2 - self.y1
