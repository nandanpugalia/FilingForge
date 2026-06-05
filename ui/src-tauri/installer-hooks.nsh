; FilingForge NSIS installer hooks.
;
; During an in-place auto-update the running app's Python engine sidecar
; (filingforge-api.exe) holds a lock on its own binary, so the installer fails
; with "Error opening file for writing ... filingforge-api.exe". We terminate the
; sidecar (and any stragglers) BEFORE files are written so the overwrite succeeds.
; Errors are ignored — on a fresh install nothing is running.

!macro NSIS_HOOK_PREINSTALL
  nsExec::Exec 'taskkill /F /T /IM filingforge-api.exe'
  Pop $0
!macroend
