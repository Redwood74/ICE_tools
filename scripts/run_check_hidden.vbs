' run_check_hidden.vbs — Windowless ICE check launcher (fallback).
'
' Runs findice-bg.exe completely hidden via the SW_HIDE (0) flag.
' Use this if you can't re-register the scheduled task but still want
' zero window flash.  The primary mechanism is the gui_scripts entry
' point (findice-bg.exe) which runs under pythonw.exe.
'
' Usage:  wscript scripts\run_check_hidden.vbs

Set fso = CreateObject("Scripting.FileSystemObject")
Set sh  = CreateObject("WScript.Shell")

' Resolve repo root (parent of the scripts\ folder containing this file)
repoRoot = fso.GetParentFolderName(fso.GetParentFolderName(WScript.ScriptFullName))
sh.CurrentDirectory = repoRoot

findiceBg = repoRoot & "\.venv\Scripts\findice-bg.exe"

' 0 = SW_HIDE (completely invisible), True = wait for exit
sh.Run """" & findiceBg & """ check-once", 0, True
