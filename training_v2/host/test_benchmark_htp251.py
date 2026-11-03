"""Protect benchmark units, warmup exclusion and sample completeness."""
import tempfile,unittest
from pathlib import Path
from benchmark_htp251 import client_samples,PACKAGE

class TimingChecks(unittest.TestCase):
    def check_csv(self,rows,warmup,runs):
        temporary=PACKAGE/'test-temp';temporary.mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(dir=temporary) as folder:
            path=Path(folder)/'profile.csv';path.write_text('metadata,2.51\nMsg Timestamp, Message, Time, Unit of Measurement, Timing Source, Event Level, Event Identifier\n'+'\n'.join(rows))
            return client_samples(path,warmup,runs)
    def test_excludes_init_backend_subevents_and_warmup(self):
        rows=['1,INIT,999999,US,NETRUN,ROOT,init','2,EXECUTE,5000,US,NETRUN,ROOT,graph','2,EXECUTE,99000,US,BACKEND,ROOT,RPC','3,EXECUTE,1500,US,NETRUN,ROOT,graph','3,EXECUTE,42,CYCLES,BACKEND,SUB-EVENT,op','4,EXECUTE,2500,US,NETRUN,ROOT,graph']
        self.assertEqual(self.check_csv(rows,1,2),([1.5,2.5],[5.0]))
    def test_refuses_incomplete_session(self):
        with self.assertRaises(AssertionError):self.check_csv(['1,EXECUTE,1500,US,NETRUN,ROOT,graph'],1,2)
    def test_refuses_wrong_units(self):
        with self.assertRaises(AssertionError):self.check_csv(['1,EXECUTE,1500,CYCLES,NETRUN,ROOT,graph'],0,1)

if __name__=='__main__':unittest.main(verbosity=2)
