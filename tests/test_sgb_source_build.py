"""SGB-013: build the repaired sources directly and track their dependencies."""
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
from sgb_native import SGB,FLAGS


class SgbSourceBuild(unittest.TestCase):
    def test_direct_source_incremental_build(self):
        with tempfile.TemporaryDirectory() as temp:
            work=Path(temp)
            for name in ['Makefile','gb_graph.w','gb_types.w','boilerplate.w']:
                shutil.copyfile(SGB/name,work/name)
            command=['make','gb_graph.o','CC=gcc','CFLAGS='+' '.join(FLAGS)]
            def build():
                result=subprocess.run(command,cwd=work,capture_output=True,timeout=30)
                self.assertEqual(result.returncode,0,result.stderr)
                return result.stdout.decode()
            self.assertIn('ctangle gb_graph.w -',build())
            self.assertNotIn('ctangle',build())
            for dependency in ['gb_graph.w','gb_types.w','boilerplate.w']:
                # Make the generated outputs older, then advance one input only.
                for name in ['gb_graph.w','gb_types.w','boilerplate.w']:
                    os.utime(work/name,(1000000000,1000000000))
                for name in ['gb_graph.c','gb_graph.o']:
                    os.utime(work/name,(1000000010,1000000010))
                os.utime(work/dependency,(1000000020,1000000020))
                self.assertIn('ctangle gb_graph.w -',build(),dependency)
                self.assertNotIn('ctangle',build())
            docs=subprocess.run(['make','-n','gb_graph.tex'],cwd=work,capture_output=True,timeout=5)
            self.assertEqual(docs.returncode,0,docs.stderr)
            self.assertIn('cweave gb_graph.w -',docs.stdout.decode())
            default=subprocess.run(['make','-n'],cwd=work,capture_output=True,timeout=5)
            self.assertEqual(default.returncode,0,default.stderr)
            self.assertIn("First 'make tests'",default.stdout.decode())


if __name__=='__main__':unittest.main()
