"""B053: native conversion must fail on stream errors, including after input."""
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]

# A real stdio stream delivers one complete clause and then fails with EIO.
# Keeping the fault outside the converter distinguishes EOF from read failure.
READ_FAILURE = r'''
#define _GNU_SOURCE
#include <stdio.h>
#include <errno.h>
#include <string.h>
#include <sys/types.h>
extern int converter_main(int, char **);
static ssize_t read_clause(void *cookie, char *buf, size_t size) {
  static size_t offset=0;
  const char data[]="x\n";
  size_t count;
  if (offset==sizeof(data)-1) { errno=EIO; return -1; }
  count=sizeof(data)-1-offset;
  if (count>size) count=size;
  memcpy(buf,data+offset,count);
  offset+=count;
  return count;
}
int main(int argc, char **argv) {
  cookie_io_functions_t io={0};
  io.read=read_clause;
  stdin=fopencookie(NULL,"r",io);
  if (!stdin) return 98;
  return converter_main(argc,argv);
}
'''


class NativeConverterStatus(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        sgb = os.environ.get('GRAPHBASE')
        if not sgb:
            raise unittest.SkipTest('Set GRAPHBASE for native converter checks')
        cls.temp = tempfile.TemporaryDirectory()
        work = Path(cls.temp.name)
        generated = work/'converter.c'
        harness = work/'read_failure.c'
        harness.write_text(READ_FAILURE)
        subprocess.run(['ctangle', str(ROOT/'programs/programs/sat-to-dimacs.w'),
                        '-', str(generated)], check=True, capture_output=True)
        cls.programs = []
        for dialect in ['gnu89', 'gnu99']:
            flags = ['gcc', '-std='+dialect, '-Wno-implicit-int', '-O1',
                     '-fsanitize=undefined,bounds', '-fno-sanitize-recover=all',
                     '-I'+sgb]
            program = work/dialect
            subprocess.run(flags+[str(generated), str(Path(sgb)/'gb_flip.c'),
                                  '-o', str(program)], check=True, capture_output=True)
            obj = work/(dialect+'.o')
            broken = work/(dialect+'-broken')
            subprocess.run(flags+['-Dmain=converter_main', '-c', str(generated),
                                  '-o', str(obj)], check=True, capture_output=True)
            subprocess.run(flags+[str(obj), str(harness), str(Path(sgb)/'gb_flip.c'),
                                  '-o', str(broken)], check=True, capture_output=True)
            cls.programs.append((program, broken))

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def test_success_returns_zero_and_keeps_clause_semantics(self):
        for program, _ in self.programs:
            result = subprocess.run([str(program), 'v0'], input=b'x x\nx ~x\n~x y\n',
                                    capture_output=True, timeout=3)
            with self.subTest(dialect=program.name):
                self.assertEqual(result.returncode, 0, result.stderr.decode())
                lines = result.stdout.decode().splitlines()
                self.assertIn('p cnf 2 2', lines)
                self.assertEqual([line.split() for line in lines if line.startswith(' ')],
                                 [['2', '-1', '0'], ['1', '0']])

    def test_buffered_output_failure_is_reported(self):
        for program, _ in self.programs:
            with open('/dev/full', 'wb') as sink:
                result = subprocess.run([str(program), 'v0'], input=b'x\n', stdout=sink,
                                        stderr=subprocess.PIPE, timeout=3)
            with self.subTest(dialect=program.name):
                self.assertNotEqual(result.returncode, 0)

    def test_read_failure_after_a_clause_is_not_clean_eof(self):
        for _, program in self.programs:
            result = subprocess.run([str(program), 'v0'], capture_output=True, timeout=3)
            with self.subTest(dialect=program.name):
                self.assertNotEqual(result.returncode, 0)
                self.assertNotIn(b'p cnf', result.stdout)
                self.assertNotIn(b'runtime error', result.stderr)

    def test_chunk_boundaries_and_tautology_rollback(self):
        names = [f'x{i}'.encode() for i in range(520)]
        for program, _ in self.programs:
            for tautology in [False, True]:
                data = b' '.join(names)+(b' ~x0' if tautology else b'')+b'\nx0\n'
                result = subprocess.run([str(program), 'v0', 'b4096'], input=data,
                                        capture_output=True, timeout=3)
                with self.subTest(dialect=program.name, tautology=tautology):
                    self.assertEqual(result.returncode, 0, result.stderr.decode())
                    lines = result.stdout.splitlines()
                    self.assertIn(b'p cnf 520 '+(b'1' if tautology else b'2'), lines)
                    clauses = [list(map(int, line.split())) for line in lines
                               if line.startswith(b' ')]
                    self.assertEqual(clauses[0], [1, 0])
                    if not tautology:
                        self.assertEqual(clauses[1], list(range(520, 0, -1))+[0])


if __name__ == '__main__':
    unittest.main()
