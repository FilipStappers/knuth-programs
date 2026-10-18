;;; Shared native debugger fixtures. -*- lexical-binding: t; -*-
(require 'ert)
(require 'cl-lib)
(defconst review-test-root
  (expand-file-name "../.." (file-name-directory load-file-name)))
(load (expand-file-name "programs/programs/gud23.el" review-test-root) nil nil t)
(load (expand-file-name "programs/programs/gdb-ui.el" review-test-root) nil nil t)

(defun review-assembler-update (pc previous-pc frame previous-frame pending queue)
  (with-temp-buffer
    (let ((gud-comint-buffer (current-buffer))
          (gdb-input-queue queue)
          (gdb-pc-address pc)
          (gdb-previous-frame-pc-address previous-pc)
          (gdb-selected-frame frame)
          (gdb-previous-frame previous-frame)
          (gdb-pending-triggers pending)
          commands)
      (cl-letf (((symbol-function 'gdb-get-buffer) (lambda (_) t))
                ((symbol-function 'gdb-enqueue-input)
                 (lambda (command) (push command commands))))
        (gdb-invalidate-assembler))
      (list commands gdb-input-queue gdb-previous-frame-pc-address gdb-previous-frame))))
