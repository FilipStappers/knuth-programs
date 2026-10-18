;;; B011 nested number matching must not change accumulator coordinates. -*- lexical-binding: t; -*-
(load (expand-file-name "debugger-fixture.el" (file-name-directory load-file-name)) nil nil t)
(ert-deftest java-marker-cuts-accumulator-at-the-complete-marker-boundary ()
  (let ((stream "Stopped p.Example.run (Example:1,234)\nTAIL\n"))
    (dolist (split (list 0 8 (length stream)))
      (let ((result (review-java-marker (list (substring stream 0 split) (substring stream split)))))
        (should (equal result (list '("Example.java" . 1234) ")\nTAIL\n" stream)))))))
(ert-run-tests-batch-and-exit)
