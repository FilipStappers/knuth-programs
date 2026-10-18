;;; B010 selected-frame identity follows MI responses. -*- lexical-binding: t; -*-
(load (expand-file-name "debugger-fixture.el" (file-name-directory load-file-name)) nil nil t)
(ert-deftest frame-handler-updates-address-with-every-selected-frame ()
  (let ((gdb-frame-address "stale") (gud-overlay-arrow-position nil))
    (dolist (record '(("0" "0x123456789abcdef0" "main") ("2" "0x20" "caller")))
      (with-temp-buffer
        (insert (format "^done,frame={level=\"%s\",addr=\"%s\",func=\"%s\",file=\"a.c\",fullname=\"/tmp/a.c\",line=\"7\"}"
                        (nth 0 record) (nth 1 record) (nth 2 record)))
        (cl-letf (((symbol-function 'gdb-get-buffer) #'ignore)) (gdb-frame-handler-1))
        (should (equal gdb-frame-address (nth 1 record)))
        (should (equal gdb-pc-address gdb-frame-address))
        (should (equal gdb-frame-number (car record)))
        (should (equal gdb-selected-frame (nth 2 record)))))))
(ert-run-tests-batch-and-exit)
