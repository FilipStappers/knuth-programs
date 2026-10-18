;;; B011 GDB action navigation balances nested blocks. -*- lexical-binding: t; -*-
(load (expand-file-name "debugger-fixture.el" (file-name-directory load-file-name)) nil nil t)
(ert-deftest script-end-skips-nested-if-while-and-commands ()
  (with-temp-buffer
    (insert "define action\nif $x\nwhile $y\nprintf \"end\"\nend\ncommands 1\n# end\ncontinue\nend\nend\nend\nnext-command\n")
    (let ((expected (save-excursion (goto-char (point-max)) (forward-line -2) (point))))
      (dolist (line '(1 2 4 8))
        (goto-char (point-min)) (forward-line (1- line))
        (gdb-script-end-of-defun)
        (should (= (point) expected))))))
(ert-deftest script-document-text-is-not-parsed-as-nested-commands ()
  (with-temp-buffer
    (insert "document action\nif this is prose\nwhile this is also prose\nend\nnext-command\n")
    (goto-char (point-min))
    (gdb-script-end-of-defun)
    (should (looking-at "end\nnext-command"))))
(ert-run-tests-batch-and-exit)
