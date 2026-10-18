from enigma_native import EnigmaNative
import subprocess


class EnigmaInputScores(EnigmaNative):
    def test_short_cribs_reject_before_setup(self):
        program=self.build('crib','''@<Process the command line@>;
printf("ACCEPTED %d %d\\n",m,mc);''')
        for crib,cipher in [('', 'ABC'),('A','ABC')]:
            result=subprocess.run([str(program),crib,cipher],capture_output=True,timeout=5)
            self.assertNotEqual(result.returncode,0)
            self.assertIn(b'2<=|plaintext|',result.stderr)
        for crib,cipher in [('AB','ABC'),('A'*25,'B'*150)]:
            result=subprocess.run([str(program),crib,cipher],capture_output=True,timeout=5)
            self.assertEqual(result.returncode,0,result.stderr.decode())
            self.assertIn(f'plaintext of length {len(crib)}'.encode(),result.stderr)
            self.assertEqual(result.stdout,
                             f'ACCEPTED {len(crib)} {len(cipher)}\n'.encode())

    def test_score_totals_stay_in_histogram(self):
        program=self.build('score','''ciphersize=atoi(argv[1]);
score[0][0][0][0][0]=atoi(argv[2]);
bestscore=maxscore; plugs[0][0]=-1; i=j=0;
@<Compute the score of |plntxt| and possibly output it@>;
printf("TALLY %d %d\\n",s,tally[s]);''')
        for length,weight in [(5,-1),(5,10000),(6,9999),(150,2147483647)]:
            with self.subTest(length=length,weight=weight):
                result=subprocess.run([str(program),str(length),str(weight)],capture_output=True,timeout=5)
                self.assertNotEqual(result.returncode,0)
                self.assertIn(b'score total',result.stderr)
        for length,weight in [(4,0),(5,0),(5,9999),(150,68)]:
            with self.subTest(length=length,weight=weight):
                total=max(0,length-4)*weight
                self.assertIn(f'TALLY {total} 1\n'.encode(),self.run_program(program,length,weight))
