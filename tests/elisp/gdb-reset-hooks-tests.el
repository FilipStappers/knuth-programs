;;; B010 all source buffers lose debugger save hooks at reset. -*- lexical-binding: t; -*-
(load (expand-file-name "debugger-fixture.el" (file-name-directory load-file-name)) nil nil t)
(ert-deftest reset-cleans-local-hooks-in-every-debugger-source-buffer ()
  (let ((sources (list (generate-new-buffer "source-a.c") (generate-new-buffer "source-b.c"))))
    (unwind-protect
        (with-temp-buffer
          (let ((gud-comint-buffer (current-buffer)))
            (cl-mapc (lambda (source mode)
                       (with-current-buffer source
                         (setq-local gud-minor-mode mode)
                         (add-hook 'after-save-hook 'gdb-create-define-alist nil t)
                         (add-hook 'after-save-hook 'ignore nil t)))
                     sources '(gdba gdbmi))
            (cl-letf (((symbol-function 'gdb-remove-breakpoint-icons) #'ignore)
                      ((symbol-function 'speedbar-timer-fn) #'ignore))
              (gdb-reset))
            (dolist (source sources)
              (with-current-buffer source
                (should-not (memq 'gdb-create-define-alist after-save-hook))
                (should (memq 'ignore after-save-hook))
                (should-not gud-minor-mode)))))
      (mapc #'kill-buffer sources))))
(ert-run-tests-batch-and-exit)
