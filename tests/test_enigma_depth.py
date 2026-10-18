from enigma_native import EnigmaNative


class EnigmaDepth(EnigmaNative):
    def test_one_based_solver_depth(self):
        program=self.build('depth','''vars=atoi(argv[1]); nonspec=clauses=vars+vars+2;
@<Launch the solver@>;''',visit='printf("DEPTH %u\\n",level-1); return 0;')
        for n in [1,63,64,65,351]:
            with self.subTest(n=n):
                self.assertEqual(self.run_program(program,n),f'DEPTH {n}\n'.encode())

