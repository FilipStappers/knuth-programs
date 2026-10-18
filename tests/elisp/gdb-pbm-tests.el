;;; B010 native fallback data obeys the PBM header. -*- lexical-binding: t; -*-
(load (expand-file-name "debugger-fixture.el" (file-name-directory load-file-name)) nil nil t)
(ert-deftest breakpoint-fallback-pbm-has-exact-binary-pixel-count ()
  (dolist (data (list breakpoint-enabled-pbm-data breakpoint-disabled-pbm-data))
    (let ((tokens (split-string data "[ \t\r\n]+" t)))
      (should (equal (seq-take tokens 3) '("P1" "10" "10")))
      (should (= (length (nthcdr 3 tokens)) 100))
      (dolist (pixel (nthcdr 3 tokens)) (should (member pixel '("0" "1")))))))
(ert-run-tests-batch-and-exit)
