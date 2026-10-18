;;; B010 bounded quoted MI values. -*- lexical-binding: t; -*-
(load (expand-file-name "debugger-fixture.el" (file-name-directory load-file-name)) nil nil t)
(ert-deftest local-value-captures-stop-at-their-own-quoted-string ()
  (let ((target (generate-new-buffer " locals-test"))
        (values '("1" "a\"b\\c"))
        (reader (symbol-function 'read)) arguments)
    (unwind-protect
        (with-temp-buffer
          (insert "^done,locals=["
                  (format "{name=\"a\",type=\"int\",value=%s}," (prin1-to-string (car values)))
                  (format "{name=\"b\",type=\"char *\",value=%s}]" (prin1-to-string (cadr values))))
          (cl-letf (((symbol-function 'gdb-get-buffer) (lambda (_) target))
                    ((symbol-function 'read)
                     (lambda (argument &rest rest)
                       (push argument arguments) (apply reader argument rest))))
            (gdb-stack-list-locals-handler))
          (should (equal (nreverse arguments) (mapcar #'prin1-to-string values)))
          (with-current-buffer target
            (should (equal (buffer-substring-no-properties (point-min) (point-max))
                           "b\tchar *\ta\"b\\c\na\tint\t1\n"))))
      (kill-buffer target))))
(ert-run-tests-batch-and-exit)
