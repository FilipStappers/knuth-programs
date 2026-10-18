"""Run native ERT suites when EMACS or a local portable runtime is available."""
import os
from pathlib import Path
import shutil
import subprocess
import unittest

ROOT=Path(__file__).resolve().parents[1]
EMACS=os.environ.get('EMACS') or shutil.which('emacs')
if not EMACS and (ROOT/'build/emacs-runtime/bin/emacs.exe').exists():
    EMACS=str(ROOT/'build/emacs-runtime/bin/emacs.exe')


@unittest.skipUnless(EMACS,'Set EMACS to a native Emacs executable')
class ElispRegressions(unittest.TestCase):
    def test_native_ert_suites(self):
        for script in sorted((ROOT/'tests/elisp').glob('*-tests.el')):
            with self.subTest(suite=script.name):
                result=subprocess.run([EMACS,'--batch','--quick','-l',str(script.relative_to(ROOT))],
                                      cwd=ROOT,capture_output=True,timeout=45)
                self.assertEqual(result.returncode,0,(result.stdout+result.stderr).decode(errors='replace'))


if __name__=='__main__': unittest.main()
