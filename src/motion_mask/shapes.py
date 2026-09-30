from mediapipe.tasks.python.components.containers import Category

from common import index_to_name_mapping


class Shape:
    def __init__(self):
        self._score = 0.0

    def update(self, blendshapes: list[Category]):
        raise NotImplementedError()

    def get_score(self):
        return self._score


class ShapeDefault(Shape):
    def __init__(self, index: int):
        super().__init__()
        self.index = index
        self.name = index_to_name_mapping[index]

        self._score: float = 0.000001

    def update(self, blendshapes: list[Category]):
        category = blendshapes[self.index]
        self._score = category.score


class ShapeForCalibration(Shape):
    def __init__(self, index: int):
        super().__init__()
        self.index = index
        self.name = index_to_name_mapping[index]

        self._score: float = 0.000001
        self.min: float = 0.000000
        self.max: float = 0.000002

        self._update_delta()

    def _update_delta(self):
        self._delta = self.max - self.min

    @property
    def delta(self):
        return self._delta

    def update(self, blendshapes: list[Category]):
        category = blendshapes[self.index]
        self._score = category.score

        if self._score < self.min:
            self.min = self._score
        elif self._score > self.max:
            self.max = self._score

        self._update_delta()
