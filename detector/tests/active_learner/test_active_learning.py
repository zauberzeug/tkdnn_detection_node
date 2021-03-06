# Learner Tests incoming
from datetime import datetime, timedelta
import pytest
from active_learner.observation import Observation
from active_learner import learner as l
from icecream import ic
import time
from learning_loop_node.detector.box_detection import BoxDetection
from learning_loop_node.detector.point_detection import PointDetection

dirt_detection = BoxDetection('dirt', 0, 0, 100, 100, 'xyz', .3)
second_dirt_detection = BoxDetection('dirt', 0, 20, 10, 10, 'xyz', .35)
conf_too_high_detection = BoxDetection('dirt', 0, 0, 100, 100, 'xyz', .61)
conf_too_low_detection = BoxDetection('dirt', 0, 0, 100, 100, 'xyz', .29)


def test_learner_confidence():
    learner = l.Learner()
    assert len(learner.low_conf_observations) == 0

    active_learning_cause = learner.add_box_detections([dirt_detection])
    assert active_learning_cause == ['lowConfidence'], \
        f'Active Learning should be done due to lowConfidence'
    assert len(learner.low_conf_observations) == 1, 'Detection should be stored'

    active_learning_cause = learner.add_box_detections([dirt_detection])
    assert len(
        learner.low_conf_observations) == 1, f'Detection should already be stored'
    assert active_learning_cause == []

    active_learning_cause = learner.add_box_detections(
        [conf_too_low_detection])
    assert len(
        learner.low_conf_observations) == 1, f'Confidence of detection too low'
    assert active_learning_cause == []

    active_learning_cause = learner.add_box_detections(
        [conf_too_high_detection])
    assert len(
        learner.low_conf_observations) == 1, f'Confidence of detection too high'
    assert active_learning_cause == []


def test_add_second_detection_to_learner():
    learner = l.Learner()
    assert len(learner.low_conf_observations) == 0
    learner.add_box_detections([dirt_detection])
    assert len(learner.low_conf_observations) == 1, 'Detection should be stored'
    learner.add_box_detections([second_dirt_detection])
    assert len(
        learner.low_conf_observations) == 2, 'Second detection should be stored'


def test_update_last_seen():
    observation = Observation(dirt_detection)
    observation.last_seen = datetime.now() - timedelta(seconds=.5)
    assert observation.is_older_than(0.5) == True


def test_forget_old_detections():
    learner = l.Learner()
    assert len(learner.low_conf_observations) == 0

    active_learning_cause = learner.add_box_detections([dirt_detection])
    assert active_learning_cause == [
        'lowConfidence'], f'Active Learning should be done due to lowConfidence.'

    assert len(learner.low_conf_observations) == 1

    learner.low_conf_observations[0].last_seen = datetime.now(
    ) - timedelta(minutes=30)
    learner.forget_old_detections()
    assert len(learner.low_conf_observations) == 1

    learner.low_conf_observations[0].last_seen = datetime.now(
    ) - timedelta(hours=1, minutes=1)
    learner.forget_old_detections()
    assert len(learner.low_conf_observations) == 0


def test_active_learner_extracts_from_json():
    detections = [
        {"category_name": "dirt",
         "x": 1366,
         "y": 1017,
         "width": 37,
         "height": 24,
         "model_name": "some_weightfile",
         "confidence": .3},
        {"category_name": "obstacle",
         "x": 0,
         "y": 0,
         "width": 37,
         "height": 24,
         "model_name": "some_weightfile",
         "confidence": .35},
        {"category_name": "dirt",
         "x": 1479,
         "y": 862,
         "width": 14,
         "height": 11,
         "model_name": "some_weightfile",
         "confidence": .2}]

    mac = '0000'
    learners = {mac: l.Learner()}

    active_learning_cause = learners[mac].add_box_detections(
        [BoxDetection.from_dict(_detection) for _detection in detections])

    assert active_learning_cause == ['lowConfidence']


def test_ignoring_similar_points():
    learner = l.Learner()
    active_learning_cause = learner.add_point_detections(
        [PointDetection('point', 100, 100, 'xyz', 0.3)])
    assert active_learning_cause == ['lowConfidence'], \
        f'Active Learning should be done due to low confidence'
    assert len(learner.low_conf_observations) == 1, 'detection should be stored'

    active_learning_cause = learner.add_point_detections(
        [PointDetection('point', 104, 98, 'xyz', 0.3)])
    assert len(
        learner.low_conf_observations) == 1, f'detection should already be stored'
    assert active_learning_cause == []
