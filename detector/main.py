import uvicorn
from fastapi import APIRouter, Request, File, UploadFile, Header
from fastapi.encoders import jsonable_encoder
from learning_loop_node import DetectorNode
from typing import Optional, List, Any
import cv2
import numpy as np
from fastapi.responses import JSONResponse
from icecream import ic
from fastapi_utils.tasks import repeat_every
from fastapi_socketio import SocketManager
from detector.tkdnn import Detector
from detector.outbox import Outbox
from detector.detection import Detection
from detector.active_learner import learner as l
from detector import helper
import asyncio
from datetime import datetime
from threading import Thread


node = DetectorNode(uuid='12d7750b-4f0c-4d8d-86c6-c5ad04e19d57', name='detector node')
sio = SocketManager(app=node)
detector = Detector()
outbox = Outbox()
router = APIRouter()
learners = {}


@router.put("/reset")
def reset_test_learner(request: Request):
    global learners
    learners = {}


@router.post("/upload")
async def upload_image(request: Request, files: List[UploadFile] = File(...)):
    for file_data in files:
        await outbox.write_file(file_data, file_data.filename)

    return 200, "OK"


@node.sio.event
async def detect(sid, data):

    try:
        np_image = np.frombuffer(data['image'], np.uint8)
        return get_detections(np_image, data.get('mac', None), data.get('tags', []))
    except Exception as e:
        helper.print_stacktrace()
        with open('/tmp/bad_img_from_socket_io.jpg', 'wb') as f:
            f.write(data['image'])
        return {'error': str(e)}


@router.post("/detect")
async def http_detect(request: Request, file: UploadFile = File(...), mac: str = Header(...), tags: Optional[str] = Header(None)):
    """
    Example Usage

        curl --request POST -H 'mac: FF:FF' -F 'file=@test.jpg' localhost:8004/detect

        for i in `seq 1 10`; do time curl --request POST -H 'mac: FF:FF' -F 'file=@test.jpg' localhost:8004/detect; done
    """
    try:
        np_image = np.fromfile(file.file, np.uint8)
    except:
        raise Exception(f'Uploaded file {file.filename} is no image file.')

    return JSONResponse(get_detections(np_image, mac, tags.split(',') if tags else []))


def get_detections(np_image, mac: str, tags: str):
    image = cv2.imdecode(np_image, cv2.IMREAD_COLOR)
    detections = detector.evaluate(image)

    thread = Thread(target=learn, args=(detections, mac, tags, image))
    thread.start()
    return {'box_detections': jsonable_encoder(detections)}


def learn(detections: List[Detection], mac: str, tags: Optional[str], cv_image) -> None:
    active_learning_causes = check_detections_for_active_learning(detections, mac)

    if any(active_learning_causes):
        tags.append(mac)
        tags.append(active_learning_causes)

        outbox.save(cv_image, detections, tags)


def check_detections_for_active_learning(detections: List[Detection], mac: str) -> List[str]:
    global learners
    {learner.forget_old_detections() for (mac, learner) in learners.items()}
    if mac not in learners:
        learners[mac] = l.Learner()

    active_learning_causes = learners[mac].add_detections(detections)
    return active_learning_causes


@node.on_event("startup")
@repeat_every(seconds=30, raise_exceptions=False, wait_first=False)
def submit() -> None:
    thread = Thread(target=outbox.upload)
    thread.start()


sids = []


@node.sio.event
def connect(sid, environ, auth):
    global sids
    sids.append(sid)


@node.on_event("shutdown")
async def shutdown():
    for sid in sids:
        await node.sio.disconnect(sid)

node.include_router(router, prefix="")

if __name__ == "__main__":
    uvicorn.run("main:node", host="0.0.0.0", port=80, lifespan='on', reload=True)
