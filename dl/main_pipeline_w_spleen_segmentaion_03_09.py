import os
import sys
import time
from fnmatch import fnmatch
import dicom2nifti
import dicom2nifti.settings as settings
#https://realpython.com/python-timer/
from datetime import datetime
import csv
from csv import DictWriter
import shutil
import configparser

settings.disable_validate_slice_increment()
os.environ['MKL_THREADING_LAYER'] = 'GNU'
#MKL_THREADING_LAYER=GNU

config = configparser.ConfigParser()
config.read('listener.ini')
    
aet = config.get('local','aet',fallback='DL')
port = int(config.get('local','port',fallback='8104'))

anon_aet = config.get('anon','aet',fallback='ANON_LISTENER')
anon_host = config.get('anon','host',fallback='localhost')
anon_port = int(config.get('anon','port',fallback='8105'))

import numpy as np
from datetime import date

today = date.today()

#MKL_THREADING_LAYER=GNU
#MKL_SERVICE_FORCE_INTEL=1

os.environ['MKL_THREADING_LAYER'] = 'GNU'
from wldicom import dicom_listener
import logging
logging.basicConfig(level=logging.INFO)
result_folder = ''

#os.makedirs(result_folder, exist_ok=True)
def complete_func(series_path):
      print('series_path:', series_path, 'complete')
      print("step 1: transferring dcm sequence is done ")
      
      now = datetime.now()
      step_1_study_received = now.strftime("%m/%d/%Y, %H:%M:%S")
      
      dicom_directory = series_path #'./PH253258034_2/'
      #First step start
      start_idx = dicom_directory.find('/')
      xxxx = dicom_directory.split('/')
#      print(xxxx)
#      print(xxxx[2])
      base_name = xxxx[2]
      nii_fn = base_name + '_0000.nii.gz'
      sub_nii_folder = result_folder + base_name +'/'
      os.makedirs(sub_nii_folder, exist_ok=True)
      output_file = sub_nii_folder +  nii_fn#'my_test_0000.nii.gz'                 
      
      dicom2nifti.dicom_series_to_nifti(dicom_directory, output_file, reorient_nifti=True)
      
      now = datetime.now()
      step_2_nifti_created = now.strftime("%m/%d/%Y, %H:%M:%S")
      
      print("step 2: converting dcm sequence to nii.gz is done ")
      
      input_folder = sub_nii_folder
      output_folder = sub_nii_folder[:-1] + '_nnUNet_seg/'
      os.makedirs(output_folder, exist_ok=True)
      
      now = datetime.now()      
      step_3_inference_start = now.strftime("%m/%d/%Y, %H:%M:%S") 
      str_cmd = 'nnUNet_predict -i ' + input_folder + ' -o ' + output_folder + ' -tr nnUNetTrainerV2 -ctr nnUNetTrainerV2CascadeFullRes -m 3d_cascade_fullres -p nnUNetPlansv2.1 -t Task009_Spleen'# --num_threads_preprocessing 1 '
      os.system(str_cmd )
      
      now = datetime.now()
      step_3_inference_finish = now.strftime("%m/%d/%Y, %H:%M:%S")

      print("step 3: nnUNet prediction is done ")
      input_metadata_fn = './spleen.json'
      input_dicom_dir =  series_path
      input_image_list = output_folder + base_name + '.nii.gz'  
      output_dicom_fn = base_name +'.dcm'
      command = 'dcmqi/bin/itkimage2segimage '
      str_cmd = command + ' --inputDICOMDirectory ' + input_dicom_dir  + ' --inputMetadata ' + input_metadata_fn + ' --inputImageList ' + input_image_list + ' --outputDICOM ' + output_dicom_fn
      os.system(str_cmd)
      
      now = datetime.now()
      step_4_dicom_seg_created = now.strftime("%m/%d/%Y, %H:%M:%S")

      print('step 4: converting nii seg to dcm is done ')
      command = 'dcm4che/bin/storescu -b %s -c %s@%s:%s ' % (aet,anon_aet,anon_host,anon_port)
      str_cmd = command + output_dicom_fn
      os.system(str_cmd)  
      print('step 5: sending seg dcm back to PACS is done ')
      
      now = datetime.now()
      step_5_set_sent = now.strftime("%m/%d/%Y, %H:%M:%S")
      print('Waiting for next subject ')
      print(step_1_study_received, step_2_nifti_created, step_3_inference_start,step_3_inference_finish, step_4_dicom_seg_created, step_5_set_sent)
#https://www.geeksforgeeks.org/how-to-append-a-new-row-to-an-existing-csv-file/
      field_names = ['dicom_seq', 'step_1_study_received', 'step_2_nifti_created', 'step_3_inference_start',
               'step_3_inference_finish', 'step_4_dicom_seg_created','step_5_set_sent']
# Dictionary that we want to add as a new row
      dict = {'dicom_seq': base_name, 'step_1_study_received': step_1_study_received, 'step_2_nifti_created': step_2_nifti_created, 'step_3_inference_start': step_3_inference_start,
        'step_3_inference_finish': step_3_inference_finish, 'step_4_dicom_seg_created': step_4_dicom_seg_created, 'step_5_set_sent': step_5_set_sent}

      shutil.rmtree(output_folder)
      shutil.rmtree(input_folder)

dicom_listener(aet=aet,port=port,data_store_path='.',timeout=30,series_complete_callback=complete_func)
