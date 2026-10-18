;;; Native Emacs regressions for BUG-037. -*- lexical-binding: t; -*-
(require 'ert)
(require 'cl-lib)
(load (expand-file-name "../../programs/programs/color-mode.el"
                        (file-name-directory load-file-name)) nil nil t)

(ert-deftest color-empty-line-paint-is-safe ()
  (with-temp-buffer
    (dotimes (color 9) (color-mode-paint-line color))
    (should (= (point-min) (point-max)))
    (color-mode-unpaint-line)))

(ert-deftest color-final-prefix-only-line-is-safe ()
  (dotimes (color 9)
    (with-temp-buffer
      (insert "Color-Mode\n" (string color))
      (setq buffer-undo-list '(original-undo-state))
      (color-decode (point-min) (point-max))
      (should (equal (buffer-string) ""))
      (should (equal buffer-undo-list '(original-undo-state))))))

(ert-deftest color-decoder-restores-undo-on-error ()
  (with-temp-buffer
    (insert "Color-Mode\n" (string 1) "line\n")
    (let ((saved (list 'original-undo-state)))
      (setq buffer-undo-list saved)
      (cl-letf (((symbol-function 'color-mode-paint-line)
                 (lambda (_) (error "Forced property error"))))
        (should-error (color-decode (point-min) (point-max))))
      (should (eq buffer-undo-list saved)))))

(ert-deftest color-complete-line-codec-roundtrip ()
  (with-temp-buffer
    (insert "Color-Mode\nplain\n")
    (dotimes (color 9) (insert (string color) (format "color%d\n" color)))
    (let ((encoded (buffer-string)))
      (color-decode (point-min) (point-max))
      (goto-char (point-min))
      (forward-line 1)
      (dotimes (color 9)
        (should (eq (get-text-property (point) 'color-mode) color))
        (forward-line 1))
      (color-encode (point-min) (point-max) (current-buffer))
      (should (equal (buffer-substring-no-properties (point-min) (point-max)) encoded)))))

(ert-run-tests-batch-and-exit)
