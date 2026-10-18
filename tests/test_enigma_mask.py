from enigma_native import EnigmaNative


class EnigmaMask(EnigmaNative):
    def test_constraint_bit_sixty_three(self):
        program=self.build('mask','''n=atoi(argv[1]);
for(k=0;k<n;k++) kbits[k]=1<<(k%26);
@<Prepare the {\mc SAT} constraints@>;
for(j=nonspec;j<clauses;j++) {
  for(k=cmem[j].start;k<cmem[j+1].start;k++) printf("%u ",mem[k].litno);
  printf("\\n");
}''')
        for n in [26,63,64]:
            with self.subTest(n=n):
                actual={frozenset(map(int,row.split())) for row in self.run_program(program,n).splitlines()}
                expected={frozenset((2*j+3,2*k+3)) for j in range(n) for k in range(j+1,n)
                          if j%26==k%26}
                expected|={frozenset(2*k+2 for k in range(n) if k%26==i) for i in range(26)}
                self.assertEqual(actual,expected)
