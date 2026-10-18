;;; B010 MI register number mapping. -*- lexical-binding: t; -*-
(load (expand-file-name "debugger-fixture.el" (file-name-directory load-file-name)) nil nil t)
(ert-deftest register-response-gaps-and-order-use-explicit-indices ()
  (dolist (records '(("0" "2") ("2" "0")))
    (let ((target (generate-new-buffer " registers-test")))
      (unwind-protect
          (with-temp-buffer
            (insert "^done,register-values=["
                    (mapconcat (lambda (n) (format "{number=\"%s\",value=\"value%s\"}" n n)) records ",") "]")
            (let ((gdb-register-names '("pc" "unavailable" "r0"))
                  (gdb-changed-registers '("2")))
              (cl-letf (((symbol-function 'gdb-get-buffer) (lambda (_) target))
                        ((symbol-function 'gdb-data-list-register-values-custom) #'ignore))
                (gdb-data-list-register-values-handler)))
            (with-current-buffer target
              (should (equal (buffer-string)
                             (mapconcat (lambda (n) (concat (if (equal n "2") "pc" "r0") "\tvalue" n "\n")) records "")))
              (goto-char (point-min))
              (search-forward "pc")
              (should (eq (get-text-property (1- (point)) 'face) 'font-lock-warning-face))))
        (kill-buffer target)))))
(ert-run-tests-batch-and-exit)
