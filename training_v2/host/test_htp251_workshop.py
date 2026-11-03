"""Local regression checks; no ADB connection or target writes."""
import contextlib,tempfile,unittest
from pathlib import Path
import numpy as np
from PIL import Image
import htp251_workshop as w
TEMP=w.PACKAGE/'test-temp';TEMP.mkdir(exist_ok=True)
@contextlib.contextmanager
def workspace_temp():
    with tempfile.TemporaryDirectory(dir=TEMP) as name:
        assert TEMP.resolve() in Path(name).resolve().parents
        yield name
class MigrationChecks(unittest.TestCase):
    def test_original_uint8_model_input_is_dequantized_for_qnn(self):
        with workspace_temp() as name:
            p=Path(name)/'mid.png';Image.new('RGB',(224,224),(128,128,128)).save(p)
            _,tensor=w.prepare_image('classification',p)
            self.assertEqual(tensor.dtype,np.dtype('<f4'));self.assertTrue(np.all(tensor==0))
    def test_recalibrated_ssd_keeps_pixel_input_for_graph_internal_normalization(self):
        with workspace_temp() as name:
            p=Path(name)/'mid.png';Image.new('RGB',(300,300),(128,128,128)).save(p)
            _,tensor=w.prepare_image('detection',p,input_mode='pixels_float32')
            self.assertTrue(np.all(tensor==128))
    def test_gesture_refuses_unaligned_non_square_input(self):
        with workspace_temp() as name:
            p=Path(name)/'wide.png';Image.new('RGB',(300,200)).save(p)
            with self.assertRaisesRegex(ValueError,'square'):w.prepare_image('gesture',p)
    def test_crop_outside_photo_is_rejected(self):
        with workspace_temp() as name:
            p=Path(name)/'small.png';Image.new('RGB',(100,100)).save(p)
            with self.assertRaisesRegex(ValueError,'outside'):w.prepare_image('gesture',p,(0,0,101,100))
    def test_detection_cannot_pass_on_one_good_box_and_many_false_duplicates(self):
        person=dict(label='person',box_yxyx=[0.1,0.1,0.9,0.9]);reference=dict(detections=[person]);bad=dict(detections=[person]*8)
        self.assertFalse(w.semantic('detection',bad,reference,[],[])['passed'])
        self.assertTrue(w.semantic('detection',reference,reference,[],[])['passed'])
    def test_segmentation_requires_overlap_not_only_some_foreground(self):
        a=np.zeros((1,257,257,21),dtype=np.float32);b=a.copy();a[:,:100,:100,15]=1;b[:,150:,150:,15]=1
        self.assertFalse(w.semantic('segmentation',{}, {},[a],[b])['passed'])
        self.assertTrue(w.semantic('segmentation',{}, {},[a],[a])['passed'])
    def test_output_mapping_refuses_ambiguous_buffers(self):
        with workspace_temp() as name:
            root=Path(name);(root/'Result_0').mkdir()
            for file in ['unknown_a','unknown_b']:np.zeros((1,3),dtype='<f4').tofile(root/'Result_0'/(file+'.raw'))
            with self.assertRaisesRegex(ValueError,'Ambiguous'):w.read_outputs(root,[dict(name='expected',shape=[1,3])])
    def test_nonfinite_model_output_is_rejected(self):
        with workspace_temp() as name:
            root=Path(name);(root/'Result_0').mkdir();np.array([np.nan],dtype='<f4').tofile(root/'Result_0/out.raw')
            with self.assertRaises(AssertionError):w.read_outputs(root,[dict(name='out',shape=[1])])
if __name__=='__main__':unittest.main(verbosity=2)
