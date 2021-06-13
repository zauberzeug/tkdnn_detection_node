import asyncio
from detector.active_learner.learner import Learner
from pydantic.types import Json
import requests
from icecream import ic
import cv2
import detector.tkdnn as detections_helper
import detector.helper as helper
from detector.helper import data_dir
from glob import glob
import os
import json
import pytest
import time
from ctypes import *

base_path = '/data'
image_path = f'{base_path}/2462abd538f8_2021-01-17_08-33-49.800.jpg'


def test_initialization(detector):
    assert len(detector.classes) == 9
    assert detector.image.w == 800
    assert detector.image.h == 800
    assert detector.image.c == 3


def test_detection(detector):
    detections = detector.evaluate(cv2.imread(image_path))
    assert len(detections) == 5
    d = detections[0]
    assert d.category_name == 'dirt'
    assert d.confidence == 85.6
    assert d.x == 1024
    assert d.y == 1355
    assert d.width == 27
    assert d.height == 33
    assert d.model_name == 'unknown model'


@pytest.mark.asyncio()
async def test_save_image_and_detections_if_mac_was_sent():
    request = requests.put('http://detection_node/reset')
    assert request.status_code == 200

    data = {('file', open(image_path, 'rb'))}
    headers = {'mac': '0:0:0:0', 'tags':  'some_tag'}
    request = requests.post('http://detection_node/detect', files=data, headers=headers)
    assert request.status_code == 200
    content = request.json()
    inferences = content['box_detections']

    expected_detection = {'category_name': 'dirt',
                          'confidence': 85.5,
                          'height': 24,
                          'model_name': 'some_weightfile',
                          'width': 37,
                          'x': 1366,
                          'y': 1017}
    assert len(inferences) == 8
    assert inferences[0] == expected_detection

    # Wait for async file saving
    for try_to_get_files in range(20):
        saved_files = helper.get_data_files()
        await asyncio.sleep(.2)
        if saved_files == 2:
            break

    assert len(saved_files) == 2

    json_filename = [file for file in saved_files if file.endswith('.json')][0]
    with open(json_filename, 'r') as f:
        json_content = json.load(f)

    box_detections = json_content['box_detections']
    assert len(box_detections) == 8
    assert box_detections[0] == expected_detection

    tags = json_content['tags']
    assert len(tags) == 3
    assert tags == ['0:0:0:0', 'some_tag', 'lowConfidence']


def test_files_are_deleted_after_sending():
    with open(f'{data_dir}/test.json', 'w') as f:
        f.write('Json testfile')
        f.close()

    with open(f'{data_dir}/test.jpg', 'w') as f:
        f.write('Jpg testfile')
        f.close()

    saved_files = helper.get_data_files()
    assert len(saved_files) == 2

    main._handle_detections()

    saved_files = helper.get_data_files()
    assert len(saved_files) == 0
