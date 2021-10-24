from datetime import datetime, timedelta


class PointDetection:

    def __init__(self, category, x, y, net, confidence):
        self.category_name = category
        self.x = x
        self.y = y
        self.model_name = net
        self.confidence = confidence

    @staticmethod
    def from_dict(detection: dict):
        return PointDetection(detection['category_name'], detection['x'], detection['y'], detection['model_name'], detection['confidence'])

    def __str__(self):
        return f'x:{int(self.x)} y: {int(self.y)}, c: {self.confidence:.2f} -> {self.category_name}'
