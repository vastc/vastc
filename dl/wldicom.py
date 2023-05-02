import signal
import os
import pynetdicom
import logging
import queue
from pynetdicom import AE
from threading import Thread,Event
from pynetdicom import AE, StoragePresentationContexts
from pynetdicom.sop_class import Verification
import datetime
import traceback

def handle_store(event, data_store, evt_q):
    ds = event.dataset
    ds.file_meta = event.file_meta

    sop_class = ds.SOPClassUID
    sop_instance = ds.SOPInstanceUID
    suid = ds.StudyInstanceUID
    series_uid = ds.SeriesInstanceUID
    accession = ds.AccessionNumber
    mrn = ds.PatientID

    path = f"{data_store}/{mrn}-{accession}/{suid}/{series_uid}"
    os.makedirs(path, mode = 0o755, exist_ok = True)
    filename = f"{path}/{suid}-{series_uid}-{sop_instance}.dcm"
    ds.save_as(filename, write_like_original=False)

    logging.info('Stored %s', filename)

    evt_q.put({'series_path':path, 'event_time':datetime.datetime.now(),'mrn':mrn, 'accession':accession})

    return 0x0000

def dicom_listener(aet, port=8104, data_store_path='.', timeout=60,series_complete_callback=lambda x: None):
    series_db = {}

    event_queue = queue.Queue()

    handlers = [(pynetdicom.evt.EVT_C_STORE, handle_store,[data_store_path, event_queue])]

    ae = AE(ae_title=aet)

    storage_sop_classes = [cx.abstract_syntax for cx in pynetdicom.AllStoragePresentationContexts]
    transfer_syntax = pynetdicom.ALL_TRANSFER_SYNTAXES[:]

    for uid in storage_sop_classes:
        ae.add_supported_context(uid, transfer_syntax)

    ae.add_supported_context(Verification)

    logging.info('Starting listener %s on port %s', aet, port)

    listener = ae.start_server(('', port), evt_handlers=handlers,block=False)

    timeout_delta = datetime.timedelta(seconds=timeout)

    int_evt = Event()

    old_sigint_handler = signal.getsignal(signal.SIGINT)

    # catch SIGINTs

    signal.signal(signal.SIGINT, lambda signum,frame:int_evt.set())

    try:
        while True:
            if int_evt.is_set():
                signal.signal(signal.SIGINT, old_sigint_handler)
                break
            try:
                evt = event_queue.get(timeout=1)
                series_path = evt['series_path']
                time = evt['event_time']
                series_db[series_path] = time
                event_queue.task_done()
                continue
            except queue.Empty:
                pass

            for k in list(series_db.keys()):
                logging.info('waiting on %s to timeout', k)
                if k in series_db and ((datetime.datetime.now()-series_db[k]) > timeout_delta):
                    try:
                        series_complete_callback(k)
                    except Exception:
                        logging.error('series callback %s for %s crashed:\n%s', series_complete_callback, k, traceback.format_exc())
                    finally:
                        del series_db[k]
    finally:
        logging.info('Stopping %s listener', aet)
        listener.shutdown()

# test and usage example

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)

    def complete_func(series_path):
        print('series_path:', series_path, 'complete')

    dicom_listener(aet='WLDICOMTEST',port=8104,data_store_path='./dcm-test-datastore',timeout=60,series_complete_callback=complete_func)
