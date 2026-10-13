import tempfile
from pathlib import Path
import unittest

from afdm_sp_joint_unrolled.budgeted_frame_store import FrameStore


class FrameStoreTests(unittest.TestCase):
    def test_resume_only_committed_matching_frames(self):
        with tempfile.TemporaryDirectory() as tmp:
            contract = dict(config=dict(arms=['a0']), source='frozen')
            store = FrameStore(tmp, contract)
            record = dict(frame_index=7, input_hashes={'y':'hash'}, arms={'a0':dict(finite=True)})
            store.save(7, record)
            resumed = FrameStore(tmp, contract, resume=True)
            self.assertEqual(resumed.load(7, dict(frame_index=7,input_hashes={'y':'hash'})),record)
            self.assertIsNone(resumed.load(8, dict(frame_index=8)))
            with self.assertRaises(ValueError):
                resumed.load(7, dict(input_hashes={'y':'different'}))
            with self.assertRaises(ValueError):
                FrameStore(tmp, dict(config=dict(arms=['a0']),source='changed'),resume=True)
            with self.assertRaises(FileExistsError):
                store.save(7,record)
            (Path(tmp)/'completed-frames/000007.json').write_text('{')
            with self.assertRaises(ValueError):
                resumed.load(7,{})


if __name__ == '__main__':
    unittest.main()
