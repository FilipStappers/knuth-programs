"""B057: real GraphBase fixtures and direct graph predicates (no RNG sampling)."""
import itertools
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from cnf_reference import satisfiable

ROOT = Path(__file__).resolve().parents[1]
SOURCES = ROOT/'programs/archives/SATexamples/sources'
GRAPHBASE = Path(os.environ.get('GRAPHBASE', ROOT.parent.parent/'sgb'))
ENV = dict(os.environ, ASAN_OPTIONS='detect_leaks=0')


def graphs():
    for n in range(1, 5):
        pairs = list(itertools.combinations(range(n), 2))
        for mask in range(1 << len(pairs)):
            yield n, mask, [edge for bit, edge in enumerate(pairs) if mask >> bit & 1]


def routable(n, edges, groups):
    """Enumerate disjoint connected vertex sets containing each terminal set."""
    for owners in itertools.product(range(-1, len(groups)), repeat=n):
        if any(owners[v] != color for color, group in enumerate(groups) for v in group):
            continue
        for color, group in enumerate(groups):
            selected = {v for v in range(n) if owners[v] == color}
            reached = {group[0]}
            while True:
                more = {b for a, b in edges if a in reached and b in selected}
                more |= {a for a, b in edges if b in reached and a in selected}
                if more <= reached:
                    break
                reached |= more
            if reached != selected:
                break
        else:
            return True
    return False


@unittest.skipUnless((GRAPHBASE/'gb_graph.c').is_file(), 'requires GRAPHBASE sources')
class GraphEncoderBoundaries(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.work = Path(cls.temp.name)
        objects = []
        for name in ['gb_graph', 'gb_io', 'gb_save']:
            obj = cls.work/(name+'.o')
            subprocess.run(['gcc', '-std=gnu99', '-Wno-implicit-int', '-O1', '-fcommon',
                            '-I', str(GRAPHBASE), '-c', str(GRAPHBASE/(name+'.c')),
                            '-o', str(obj)], check=True, capture_output=True)
            objects.append(str(obj))
        flags = ['-std=gnu99', '-Wno-implicit-int', '-O1', '-fcommon',
                 '-fsanitize=address,undefined,bounds', '-fno-sanitize-recover=all',
                 '-I', str(GRAPHBASE)]
        cls.programs = {}
        for name in ['connection', 'tseytin', 'tseytin-local',
                     'tseytin-small', 'tseytin-small-local']:
            generated = cls.work/(name+'.c')
            source = SOURCES/f'sat-{name}.w'
            if name.startswith('tseytin-'):
                # Isolate one vertex's original clauses to test its parity truth
                # table: the complete odd-charge formula is always UNSAT, so its
                # decision alone cannot verify individual vertex constraints.
                source = cls.work/(name+'.w')
                text = (SOURCES/'sat-tseytin.w').read_text()
                if 'small' in name:
                    assert text.count('char bit[1000];') == 1
                    text = text.replace('char bit[1000];', 'char bit[2];')
                if name.endswith('-local'):
                    loop = 'for (v=g->vertices;v<g->vertices+g->n;v++) {'
                    assert text.count(loop) == 1
                    text = text.replace('@c\n', '@c\n#include <stdlib.h>\n', 1)
                    text = text.replace(loop, loop+
                        '\n  if (v-g->vertices!=atoi(getenv("TEST_VERTEX"))) continue;', 1)
                source.write_text(text)
            subprocess.run(['ctangle', str(source), '-', str(generated)],
                           cwd=GRAPHBASE, check=True, capture_output=True)
            program = cls.work/name
            subprocess.run(['gcc', *flags, str(generated), *objects, '-o', str(program)],
                           check=True, capture_output=True)
            cls.programs[name] = program
        fixture = cls.work/'fixture.c'
        fixture.write_text(r'''
#include <stdio.h>
#include <stdlib.h>
#include "gb_graph.h"
#include "gb_save.h"
int main(int argc, char **argv) {
  int n=atoi(argv[1]), mask=atoi(argv[2]), i,j,bit=0;
  char name[2]={0,0};
  Graph *g=gb_new_graph(n);
  if (!g) return 1;
  for (i=0;i<n;i++) {
    name[0]='a'+i;
    g->vertices[i].name=gb_save_string(name);
  }
  for (i=0;i<n;i++) for (j=i+1;j<n;j++,bit++)
    if (mask&(1<<bit)) gb_new_edge(g->vertices+i,g->vertices+j,1);
  return save_graph(g,argv[3]);
}
''')
        writer = cls.work/'fixture'
        subprocess.run(['gcc', *flags, str(fixture), *objects, '-o', str(writer)],
                       check=True, capture_output=True)
        for n, mask, _ in graphs():
            subprocess.run([str(writer), str(n), str(mask), str(cls.work/f'{n}-{mask}.gb')],
                           check=True, capture_output=True, env=ENV)

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def encode(self, name, n, mask, text='', vertex=None):
        env = ENV if vertex is None else dict(ENV, TEST_VERTEX=str(vertex))
        result = subprocess.run([str(self.programs[name]), str(self.work/f'{n}-{mask}.gb')],
                                input=text.encode(), capture_output=True, timeout=5, env=env)
        self.assertEqual(result.returncode, 0, result.stderr.decode())
        self.assertNotIn(b'runtime error', result.stderr)
        self.assertNotIn(b'AddressSanitizer', result.stderr)
        return [line.split() for line in result.stdout.decode().splitlines()
                if line.strip() and not line.startswith('~ ')]

    def connect(self, n, mask, groups):
        text = ''.join(' '.join(chr(ord('a')+v) for v in group)+'\n' for group in groups)
        return self.encode('connection', n, mask, text)

    def test_isolated_endpoint_witnesses(self):
        # First two: both isolated and only one isolated; last two reverse the root.
        for n, mask, pair in [(2, 0, [0, 1]), (3, 1, [0, 2]),
                               (3, 1, [2, 0]), (3, 1, [1, 2])]:
            with self.subTest(n=n, mask=mask, pair=pair):
                self.assertFalse(satisfiable(self.connect(n, mask, [pair])))

    def test_all_small_terminal_pairs_match_reachability(self):
        for n, mask, edges in graphs():
            for pair in itertools.combinations(range(n), 2):
                self.assertEqual(satisfiable(self.connect(n, mask, [pair])),
                                 routable(n, edges, [pair]), (n, mask, pair))

    def test_disjoint_groups_and_singletons(self):
        for n, mask, edges in graphs():
            groups_to_test = [[[v]] for v in range(n)]
            if n >= 3:
                for pair in itertools.combinations(range(n), 2):
                    for blocker in set(range(n))-set(pair):
                        # Also reverse group order to check singleton bookkeeping.
                        groups_to_test += [[list(pair), [blocker]], [[blocker], list(pair)]]
                groups_to_test += [[list(range(n))]]
            if n == 4:
                for mate in range(1, 4):
                    groups_to_test += [[[0, mate], sorted(set(range(n))-{0, mate})]]
            for groups in groups_to_test:
                self.assertEqual(satisfiable(self.connect(n, mask, groups)),
                                 routable(n, edges, groups), (n, mask, groups))

    def test_isolated_parity_vertices_terminate(self):
        for n, mask in [(1, 0), (2, 0), (3, 1)]:
            with self.subTest(n=n, mask=mask):
                try:
                    result = subprocess.run([str(self.programs['tseytin']),
                                             str(self.work/f'{n}-{mask}.gb')],
                                            stdout=subprocess.DEVNULL, stderr=subprocess.PIPE,
                                            timeout=0.3, env=ENV)
                except subprocess.TimeoutExpired:
                    self.fail('Isolated-vertex parity generation did not terminate')
                self.assertEqual(result.returncode, 0, result.stderr.decode())
                self.assertNotIn(b'runtime error', result.stderr)
                self.assertNotIn(b'AddressSanitizer', result.stderr)

    def test_tseytin_complete_formulas_are_contradictory(self):
        for n, mask, _ in graphs():
            self.assertFalse(satisfiable(self.encode('tseytin', n, mask)), (n, mask))

    def test_individual_vertex_parities_match_incident_edge_assignments(self):
        for n, mask, edges in graphs():
            for vertex in range(n):
                incident = [edge for edge in edges if vertex in edge]
                formula = self.encode('tseytin-local', n, mask, vertex=vertex)
                for bits in itertools.product([0, 1], repeat=len(incident)):
                    fixed = [[('' if bit else '~')+chr(ord('a')+u)+'.'+chr(ord('a')+v)]
                             for (u, v), bit in zip(incident, bits)]
                    self.assertEqual(satisfiable(formula+fixed), sum(bits) % 2 == (vertex == 0),
                                     (n, mask, vertex, bits))

    def test_parity_capacity_rejects_before_bit_enumeration(self):
        # Shrink only bit storage so a three-edge star reaches the same boundary
        # after a few clauses, rather than requiring 2**1000 original clauses.
        for mask, vertex in [(7, 0), (52, 3)]:
            with self.subTest(mask=mask, vertex=vertex):
                result = subprocess.run([str(self.programs['tseytin-small-local']),
                                         str(self.work/f'4-{mask}.gb')],
                                        capture_output=True, timeout=5,
                                        env=dict(ENV, TEST_VERTEX=str(vertex)))
                self.assertNotEqual(result.returncode, 0)
                self.assertIn(b'degree', result.stderr)
                self.assertIn(b'at most 2', result.stderr)
                self.assertNotIn(b'runtime error', result.stderr)
                self.assertNotIn(b'AddressSanitizer', result.stderr)
                self.assertFalse(any(line and not line.startswith(b'~ ')
                                     for line in result.stdout.splitlines()))

    def test_parity_capacity_preserves_supported_vertex_truth_tables(self):
        for n, mask, edges in graphs():
            for vertex in range(n):
                incident = [edge for edge in edges if vertex in edge]
                if len(incident) > 2:
                    continue
                formula = self.encode('tseytin-small-local', n, mask, vertex=vertex)
                for bits in itertools.product([0, 1], repeat=len(incident)):
                    fixed = [[('' if bit else '~')+chr(ord('a')+u)+'.'+chr(ord('a')+v)]
                             for (u, v), bit in zip(incident, bits)]
                    self.assertEqual(satisfiable(formula+fixed), sum(bits) % 2 == (vertex == 0),
                                     (n, mask, vertex, bits))

    def test_connection_final_records_match_newline_terminated_records(self):
        for text in [b'a b', b'  a b   ', b'a', b'   ', b'a b\nc', b' '*76+b'a b']:
            with self.subTest(text=text):
                results = [subprocess.run([str(self.programs['connection']), str(self.work/'4-63.gb')],
                                          input=record, capture_output=True, timeout=5, env=ENV)
                           for record in [text, text+b'\n']]
                for result in results:
                    self.assertEqual(result.returncode, 0, result.stderr.decode())
                    self.assertNotIn(b'runtime error', result.stderr)
                    self.assertNotIn(b'AddressSanitizer', result.stderr)
                self.assertEqual(results[0].stdout, results[1].stdout)

    def test_connection_rejects_oversized_and_nul_records(self):
        for text in [b' '*77+b'a b\n', b' '*1000+b'a b', b'a\0 b\n', b'\0\n',
                     b'a b\0c\n']:
            with self.subTest(text=text[:85]):
                result = subprocess.run([str(self.programs['connection']), str(self.work/'4-63.gb')],
                                        input=text, capture_output=True, timeout=5, env=ENV)
                self.assertNotEqual(result.returncode, 0)
                self.assertNotIn(b'runtime error', result.stderr)
                self.assertNotIn(b'AddressSanitizer', result.stderr)
                self.assertFalse(any(line and not line.startswith(b'~ ')
                                     for line in result.stdout.splitlines()))

    def test_connection_input_read_error_is_not_clean_eof(self):
        descriptor = os.open(self.work, os.O_RDONLY)
        try:
            result = subprocess.run([str(self.programs['connection']), str(self.work/'4-63.gb')],
                                    stdin=descriptor, capture_output=True, timeout=5, env=ENV)
        finally:
            os.close(descriptor)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn(b'input', result.stderr.lower())


if __name__ == '__main__':
    unittest.main()
