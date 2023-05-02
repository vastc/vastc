import os
import pynetdicom
import logging
import queue
import sqlite3
from pynetdicom import AE
from threading import Thread
from pynetdicom import AE, StoragePresentationContexts
from pynetdicom.sop_class import Verification
import pydicom
from pathlib import Path
import anon
import seg_count
import configparser

logging.basicConfig(level=logging.INFO)

storage_sop_classes = [cx.abstract_syntax for cx in pynetdicom.StoragePresentationContexts]

def process_thread(q,aet,dest_ae,dest_addr,dest_port):
    ae = AE(ae_title=aet)

    sop_ts = []

    assoc = None    
    running = True
    logging.info('%s processing thread running', dest_ae) 
    while running:
        
        ds = q.get()

        if ds == None:
            running = False
        else:
            sop_ts_pair = (ds.file_meta.MediaStorageSOPClassUID,ds.file_meta.TransferSyntaxUID)
            if  sop_ts_pair not in sop_ts:
                logging.info('%s processing thread updating PCs %s', dest_ae, sop_ts_pair)
                add_pc = True
                ae.requested_contexts = []

                ae.add_requested_context(sop_ts_pair[0], sop_ts_pair[1])
                sop_ts = [sop_ts_pair]
                
                if assoc != None and assoc.is_established:
                    assoc.release()
                    assoc = None
            if assoc == None or (((not assoc.is_established) or assoc.is_aborted) and not assoc.is_rejected):
                assoc = ae.associate(ae_title=dest_ae,addr=dest_addr,port=dest_port)
            if assoc != None and assoc.is_rejected:
                logging.error('%s Assoc Rejected', dest_ae)
                q.task_done()
                continue
            logging.info('%s processing %s %s', dest_ae, ds.PatientID, ds.StudyInstanceUID)
            if assoc.is_established:
                logging.info('%s Sending %s', dest_ae, ds.StudyInstanceUID)                
                status = assoc.send_c_store(ds)
                
        q.task_done()
        if q.empty() and (assoc != None) and assoc.is_established:
            logging.info('%s processing thread releasing assoc', dest_ae)
            assoc.release()
            assoc = None
    logging.info('%s processing thread stopping',dest_ae)
    
def handle_store(event, q, q2, series_match_list):
    ds = event.dataset
    ds.file_meta = event.file_meta

    sop_class = ds.SOPClassUID
    sop_instance = ds.SOPInstanceUID
    suid = ds.StudyInstanceUID
    accession = ds.AccessionNumber
    mrn = ds.PatientID

    if ds.Modality == 'SEG':
        logging.info('C-STORE SEG object suid %s, forwarding to archive and generating SR object', suid)
        q.put(ds)
        try:
            sr = seg_count.make_vol_sr(ds)
            if sr != None:
                q.put(sr)
        except:
            pass
        finally:
            return 0x0000

    # skip series if using series filter and it does not match a valid series description
    if series_match_list != None:
        if 'SeriesDescription' in ds:
            sd = series.SeriesDescription
        else:
            sd = ''
        if sd == '' or not (any(a in sd.strip().lower().replace(' ','') for a in series_match_list)):
            logging.info('C-STORE, Suid: %s, SeriesDescription %s not in series match, skipping', suid, repr(sd))
            return 0x0000

    logging.info('C-STORE, Suid: %s Inst: %s Syntax: %s PID: %s, Acc: %s',suid, sop_instance,event.context.transfer_syntax,mrn,accession)
    logging.info('C-STORE anonymizing')
    anon.anonymize_dataset(ds,anon.rules,True)
    anon_mrn = ds.PatientID
    anon_acc = ds.AccessionNumber
    logging.info('C-STORE anon_acc %s, anon_mrn %s', anon_acc, anon_mrn)

    q.put(ds)
    q2.put(ds)
    
    return 0x0000

if __name__ == '__main__':
    config = configparser.ConfigParser()
    config.read('listener.ini')
    
    aet = config.get('local','aet',fallback='ANON_LISTENER')
    port = int(config.get('local','port',fallback='8104'))

    series_match_file = config.get('local','series_match_file',fallback=None)

    if series_match_file:
        try:
            logging.info('Reading series_match_file %s',series_match_file)
            with open(series_match_file,'r') as f:
                raw_series_match_list = f.readlines()

                # normalize match list
                series_match_list = [a.strip().lower().replace(' ','') for a in raw_series_match_list if a.strip() != '']
                if len(series_match_list) == 0:
                    logging.info('Series match file %s is empty, disabling series match', series_match_list)
                    series_match_list = None
        except:
            logging.error('Error reading series_match_file %s, disabling series match',series_match_file)
            series_match_list = None
    else:
        logging.info('no series match file configured, disabling series match')
        series_match_list = None    
    
    process_queue = queue.Queue()
    process_queue2 = queue.Queue()

    handlers = [(pynetdicom.evt.EVT_C_STORE, handle_store,[process_queue,process_queue2,series_match_list])]

    ae = AE(ae_title=aet)

    storage_sop_classes = [cx.abstract_syntax for cx in pynetdicom.AllStoragePresentationContexts]
    transfer_syntax = pynetdicom.ALL_TRANSFER_SYNTAXES[:]

    for uid in storage_sop_classes:
         ae.add_supported_context(uid, transfer_syntax)

    ae.add_supported_context(Verification)
    
    archive_aet = config.get('archive','aet',fallback='DCM4CHEE')
    archive_host = config.get('archive','host',fallback='localhost')
    archive_port = int(config.get('archive','port',fallback='11112'))

    dl_aet = config.get('dl','aet',fallback='DL')
    dl_host = config.get('dl','host',fallback='localhost')
    dl_port = int(config.get('dl','port',fallback='8104'))
    
    logging.info('Starting processing threads')
    c_store_process = Thread(target=process_thread,args=(process_queue,aet,archive_aet,archive_host,archive_port))
    c_store_process2 = Thread(target=process_thread,args=(process_queue2,aet,dl_aet,dl_host,dl_port))

    c_store_process.start()
    c_store_process2.start()

    logging.info('Starting listener')

    ae.start_server(('', port), evt_handlers=handlers)

    logging.info('exiting')

    process_queue.put(None)
    process_queue2.put(None)

    process_queue.join()
    process_queue2.join()

    c_store_process.join()
    c_store_process2.join()
