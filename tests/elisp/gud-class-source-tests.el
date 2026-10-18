;;; B011 Java class lookup uses the requested source line. -*- lexical-binding: t; -*-
(load (expand-file-name "debugger-fixture.el" (file-name-directory load-file-name)) nil nil t)
(require 'cc-mode)
(ert-deftest java-class-lookup-uses-line-and-preserves-source-point ()
  (let* ((directory (make-temp-file "gud-class-" t))
         (classpath (expand-file-name "cp.[x]" directory))
         (file (expand-file-name "p/Outer.java" classpath)) buffer)
    (unwind-protect
        (progn
          (make-directory (file-name-directory file) t)
          (with-temp-file file
            (insert "package p;\nclass Outer {\n  class Inner {\n    int member;\n  }\n}\n"))
          (setq buffer (find-file-noselect file))
          (with-current-buffer buffer
            (java-mode)
            (goto-char (point-min))
            (let ((saved (point)) (gud-jdb-use-classpath t)
                  (gud-jdb-sourcepath nil) (gud-jdb-classpath (list "/p" classpath)))
              (should (equal (gud-find-class file 4) "p.Outer$Inner"))
              (should (= (point) saved))
              (should (equal (gud-find-class file 2) "p.Outer"))
              (should (= (point) saved)))))
      (when (buffer-live-p buffer) (kill-buffer buffer))
      (delete-directory directory t))))
(ert-run-tests-batch-and-exit)
