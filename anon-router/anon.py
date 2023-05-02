import csv
import argparse
from dicomanonymizer import *
import hashlib
import uuid
import os

# ''.join(['%x' % a for a in os.urandom(16)]).encode('utf-8')
SALT = b'9693a0733ae7d13df59d4c5cbb123a45'

def bytes_to_digits(b,l):
    num = int.from_bytes(b,'big')
    out_str = ""
    for i in range(0, l):
        (num, r) = divmod(num, 10)
        if i == 0 and r == 0:
            r = 1
        out_str += str(r)
    return out_str

def bytes_to_uid(b):
    return '2.25.'+str(uuid.UUID(bytes=b[:16], version=4).int)

def hash_it_str(s):
    return bytes_to_digits(hashlib.sha1(SALT+s.encode('utf-8')).digest(),9)

def hash_it(dataset, tag):
    element = dataset.get(tag)
    if element is not None:
        element.value = bytes_to_digits(hashlib.sha1(SALT+element.value.encode('utf-8')).digest(),9)

def mrn_hash_it(dataset, tag):
    element = dataset.get(tag)
    if element is not None:
        element.value = 'PH'+bytes_to_digits(hashlib.sha1(SALT+element.value.encode('utf-8')).digest(),9)
        
def hash_uid(dataset, tag):
    element = dataset.get(tag)
    if element is not None:
        hash_bytes = hashlib.sha1(SALT+element.value.encode('utf-8')).digest()
        element.value = bytes_to_uid(hash_bytes)    

rules = {}        
for tag in U_TAGS:
    rules[tag] = hash_uid

rules[(0x0008, 0x0050)] = hash_it
rules[(0x0010, 0x0020)] = mrn_hash_it
