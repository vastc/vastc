import pydicom
import highdicom
from pydicom.sr.codedict import codes
import sys
import math

def make_vol_sr(ds):
    data = ds[0x7fe0, 0x010].value

    voxel_count = 0

    for b in data:
        voxel_count += b.bit_count()

    x = ds[0x5200,0x9229][0][0x0028,0x9110][0][0x0028,0x0030][0]
    y = ds[0x5200,0x9229][0][0x0028,0x9110][0][0x0028,0x0030][1]
    z = ds[0x5200,0x9229][0][0x0028,0x9110][0][0x18,0x50].value

    voxel_vol = x*y*z

    vol = math.ceil((voxel_vol * voxel_count) / 100.0) / 10.0

#    item = highdicom.sr.content.NumContentItem(name=codes.DCM.VolumeEstimatedFromThreeOrMoreNonCoplanar2DRegions,value=vol, unit=codes.UCUM.CubicCentimeter,relationship_type=highdicom.sr.RelationshipTypeValues.CONTAINS)
    item = highdicom.sr.TextContentItem(name=highdicom.sr.CodedConcept(value='SegVol',scheme_designator='99WL3', meaning='Segmentation Volume'), value='Spelnic vol %g mL' % (vol),relationship_type=highdicom.sr.RelationshipTypeValues.CONTAINS)

    container = highdicom.sr.ContainerContentItem(name=highdicom.sr.CodedConcept(value='SegVolReport',scheme_designator='99WL3', meaning='Segmentation Volume Report'))

    cs = highdicom.sr.ContentSequence(is_root=False,items=[item])

    container.ContentSequence = cs

    sr = highdicom.sr.EnhancedSR(evidence=[ds],
                                 content=container,
                                 instance_number=1,
                                 series_number=400,
                                 series_instance_uid=pydicom.uid.generate_uid(prefix=None),
                                 sop_instance_uid=pydicom.uid.generate_uid(prefix=None))
    return sr;

if __name__ == '__main__':
    ds = pydicom.dcmread('seg-test.dcm')
    sr = make_vol_sr(ds)
    print(sr)    
    sr.save_as('sr-test.dcm', write_like_original=False)
