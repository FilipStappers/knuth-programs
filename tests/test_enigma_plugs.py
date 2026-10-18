from enigma_native import EnigmaNative


class EnigmaPlugs(EnigmaNative):
    def test_twenty_six_self_plugs_and_sentinel(self):
        program=self.build('plugs','''{
  unsigned int level=27,p,j,k;
  for(k=0;k<26;k++) klass[k]=loc(k,k),link[klass[k]]=klass[k],move[k+1]=0;
  @<Visit the {\mc SAT} solution found@>;
  for(k=0;k<=26;k++) printf("%d\\n",plugs[0][k]);
}''')
        expected=[sum(26-i for i in range(k)) for k in range(26)]+[-1]
        self.assertEqual(list(map(int,self.run_program(program).split())),expected)

