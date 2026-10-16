"""B061: benchmark argv and failure propagation, with command doubles only."""
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT/'programs/archives/SATexamples/sources/gates-stuck-hardest.sh'
CASES = [('1W21#10', '1W21#10'), ('0W21#18', '0W21#18'), ('1W21#19', '1W21#19'),
         ('0D29:8#16', '0D290816'), ('0D34:13#3', '0D341303'), ('0D34:13#8', '0D341308'),
         ('0D34:13#9', '0D341309'), ('0B41:41', '0B41:41'), ('0D42:3#3', '0D42:3#3'),
         ('0D42:3#7', '0D42:3#7'), ('0D42:3#8', '0D42:3#8'), ('0D42:13#2', '0D421302'),
         ('0B42:42', '0B42:42'), ('0D43:9#2', '0D43:9#2'), ('0B43:43', '0B43:43'),
         ('0D44:10#2', '0D441002')]


class BenchmarkDriver(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.work = Path(self.temp.name)
        self.log = self.work/'calls.jsonl'
        self.scratch = self.work/'scratch'
        self.scratch.mkdir()
        stub = r'''#!/usr/bin/env python3
import json, os, pathlib, sys
stage = 'producer' if pathlib.Path(sys.argv[0]).name.startswith('sat-gates') else 'solver'
log = pathlib.Path(os.environ['CALL_LOG'])
calls = [json.loads(line) for line in log.read_text().splitlines()] if log.exists() else []
row = 1+sum(call['stage'] == stage for call in calls)
data = sys.stdin.read() if stage == 'solver' else None
with log.open('a') as out:
    out.write(json.dumps(dict(stage=stage, row=row, args=sys.argv[1:], data=data))+'\n')
if stage == 'producer':
    print('a b')
else:
    print('solver stdout must be discarded')
if stage == os.environ.get('FAIL_STAGE') and row == int(os.environ.get('FAIL_ROW', '0')):
    print(stage+' failed deliberately', file=sys.stderr)
    sys.exit(23 if stage == 'producer' else 24)
'''
        for name in ['sat-gates-stuck-namekludge', 'sat13']:
            path = self.work/name
            path.write_text(stub)
            path.chmod(0o755)
        self.env = dict(os.environ, PATH=str(self.work)+os.pathsep+os.environ['PATH'],
                        CALL_LOG=str(self.log), TMPDIR=str(self.scratch))

    def run_driver(self, args, **extra):
        if self.log.exists():
            self.log.unlink()
        result = subprocess.run(['sh', str(SCRIPT), *args], cwd=self.work,
                                capture_output=True, timeout=10, env=dict(self.env, **extra))
        calls = [json.loads(line) for line in self.log.read_text().splitlines()] \
            if self.log.exists() else []
        self.assertEqual(list(self.scratch.iterdir()), [], 'Temporary input was not cleaned up')
        return result, calls

    def test_valid_seeds_preserve_all_sixteen_cases(self):
        for seed in ['17', '-2147483648', '2147483647', '+007']:
            with self.subTest(seed=seed):
                result, calls = self.run_driver([seed])
                self.assertEqual(result.returncode, 0, result.stderr.decode())
                self.assertEqual(result.stdout.decode().splitlines(), [label for label, _ in CASES])
                self.assertEqual(len(calls), 32)
                for index, (_, fault) in enumerate(CASES):
                    producer, solver = calls[2*index:2*index+2]
                    self.assertEqual(producer['args'], ['/tmp/prod,16,32-wires.gb', fault])
                    self.assertEqual(solver['args'], ['h9', 's'+seed])
                    self.assertEqual(solver['data'], 'a b\n')

    def test_invalid_seeds_reject_before_starting_commands(self):
        for args in [[], ['1', '2'], [''], ['17 extra'], ['M*'], ['+'], ['--1'],
                     ['2147483648'], ['-2147483649'], ['9'*100]]:
            with self.subTest(args=args):
                (self.work/'sMATCH').touch()
                result, calls = self.run_driver(args)
                self.assertNotEqual(result.returncode, 0)
                self.assertEqual(calls, [])
                self.assertEqual(result.stdout, b'')
                self.assertIn(b'seed', result.stderr.lower())

    def test_first_middle_and_last_command_failures_propagate(self):
        for stage, status in [('producer', 23), ('solver', 24)]:
            for row in [1, 8, 16]:
                with self.subTest(stage=stage, row=row):
                    result, calls = self.run_driver(['17'], FAIL_STAGE=stage, FAIL_ROW=str(row))
                    self.assertEqual(result.returncode, status, result.stderr.decode())
                    self.assertEqual(result.stdout.decode().splitlines(),
                                     [label for label, _ in CASES[:row]])
                    self.assertEqual(len(calls), 2*row-(stage == 'producer'))
                    self.assertIn(b'failed', result.stderr)


if __name__ == '__main__':
    unittest.main()
