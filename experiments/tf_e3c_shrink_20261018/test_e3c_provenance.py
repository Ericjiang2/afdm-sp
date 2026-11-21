import hashlib
from pathlib import Path
import tempfile
import unittest
from e3c_provenance import ALIASES,resolve_frozen


class RelocationContracts(unittest.TestCase):
    def test_aliases_and_failures(self):
        for old,new in ALIASES.items():
            with self.subTest(old=old),tempfile.TemporaryDirectory() as tmp:
                root=Path(tmp)
                path=root/new/'src'/'module.py'
                path.parent.mkdir(parents=True)
                path.write_text('frozen bytes\n')
                digest=hashlib.md5(path.read_bytes()).hexdigest()
                manifest=root/'SOURCE_MD5.txt'
                rel=f'{old}/src/module.py'
                manifest.write_text(f'{digest} {rel}\n')
                result=resolve_frozen(root,manifest)
                self.assertEqual(result[rel]['actual_path'],str(path.resolve()))
                with self.assertRaisesRegex(RuntimeError,'loaded frozen module mismatch'):
                    resolve_frozen(root,manifest,loaded_md5={'module':'0'*32})
                path.write_text('changed')
                with self.assertRaisesRegex(RuntimeError,'md5 mismatch'):
                    resolve_frozen(root,manifest)
                path.unlink()
                with self.assertRaisesRegex(FileNotFoundError,'absent'):
                    resolve_frozen(root,manifest)

    def test_actual_loaded_source_dominates_coexisting_paths(self):
        for old,new in ALIASES.items():
            with self.subTest(old=old),tempfile.TemporaryDirectory() as tmp:
                project=Path(tmp)
                root=project/'experiments'
                canonical=root/old/'src'/'receiver.py'
                actual=root/new/'src'/'receiver.py'
                canonical.parent.mkdir(parents=True)
                actual.parent.mkdir(parents=True)
                canonical.write_text('wrong canonical bytes')
                actual.write_text('expected loaded bytes')
                digest=hashlib.md5(actual.read_bytes()).hexdigest()
                manifest=root/'SOURCE_MD5.txt'
                rel=f'{old}/src/receiver.py'
                manifest.write_text(f'{digest} {rel}\n')
                loaded={'receiver':str(actual.relative_to(project))}
                result=resolve_frozen(root,manifest,loaded_paths=loaded)
                self.assertEqual(result[rel]['actual_path'],str(actual.resolve()))
                # Correct dormant canonical bytes cannot conceal a wrong import.
                canonical.write_bytes(actual.read_bytes())
                actual.write_text('wrong actually loaded bytes')
                with self.assertRaisesRegex(RuntimeError,'md5 mismatch'):
                    resolve_frozen(root,manifest,loaded_paths=loaded)
                # Nor can a missing actual source fall back to the good canonical.
                actual.unlink()
                with self.assertRaisesRegex(FileNotFoundError,'absent'):
                    resolve_frozen(root,manifest,loaded_paths=loaded)


if __name__=='__main__':
    unittest.main()
