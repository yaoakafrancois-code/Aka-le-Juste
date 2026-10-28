; Installateur Windows de CacaoCoop (NSIS 3).
; Construit par : python outils/construire_portable.py --installateur
; Source : le dossier portable dist/CacaoCoop (Python embarqué + application).

Unicode true
!include "MUI2.nsh"

!ifndef VERSION
  !define VERSION "1.0.0"
!endif
!ifndef SOURCE
  !define SOURCE "..\dist\CacaoCoop"
!endif
!ifndef SORTIE
  !define SORTIE "..\dist\Installer-CacaoCoop.exe"
!endif

!define NOM "CacaoCoop"
!define CLE_DESINSTALLATION "Software\Microsoft\Windows\CurrentVersion\Uninstall\CacaoCoop"

Name "${NOM}"
OutFile "${SORTIE}"
; Installation dans le profil de l'utilisateur : aucun droit administrateur, et le dossier des données reste modifiable.
InstallDir "$LOCALAPPDATA\CacaoCoop"
InstallDirRegKey HKCU "${CLE_DESINSTALLATION}" "InstallLocation"
RequestExecutionLevel user
SetCompressor /SOLID lzma
BrandingText "CacaoCoop ${VERSION}"
VIProductVersion "${VERSION}.0"
VIAddVersionKey "ProductName" "CacaoCoop"
VIAddVersionKey "FileDescription" "Gestion des achats et de la collecte de cacao"
VIAddVersionKey "FileVersion" "${VERSION}"
VIAddVersionKey "ProductVersion" "${VERSION}"
VIAddVersionKey "LegalCopyright" "CacaoCoop"

!define MUI_ICON "${SOURCE}\static\icones\icone.ico"
!define MUI_UNICON "${SOURCE}\static\icones\icone.ico"
!define MUI_WELCOMEPAGE_TITLE "Installation de CacaoCoop ${VERSION}"
!define MUI_WELCOMEPAGE_TEXT "Ce programme va installer CacaoCoop, le logiciel de gestion des achats et de la collecte de cacao.$\r$\n$\r$\nSi CacaoCoop est déjà installé, il sera mis à jour : vos données sont conservées. Pensez à faire une sauvegarde avant.$\r$\n$\r$\nFermez CacaoCoop s'il est ouvert, puis cliquez sur Suivant."
!define MUI_FINISHPAGE_RUN "$INSTDIR\CacaoCoop.bat"
!define MUI_FINISHPAGE_RUN_TEXT "Démarrer CacaoCoop maintenant"
!define MUI_FINISHPAGE_SHOWREADME "$INSTDIR\GUIDE_INSTALLATION.txt"
!define MUI_FINISHPAGE_SHOWREADME_TEXT "Lire le guide d'installation"
!define MUI_FINISHPAGE_SHOWREADME_NOTCHECKED

!insertmacro MUI_PAGE_WELCOME
!insertmacro MUI_PAGE_DIRECTORY
!insertmacro MUI_PAGE_INSTFILES
!insertmacro MUI_PAGE_FINISH
!insertmacro MUI_UNPAGE_CONFIRM
!insertmacro MUI_UNPAGE_INSTFILES
!insertmacro MUI_LANGUAGE "French"

!macro SupprimerProgramme
  ; Supprime le programme mais jamais les dossiers « data » (base de données, pièces) et « sauvegardes ».
  RMDir /r "$INSTDIR\python"
  RMDir /r "$INSTDIR\config"
  RMDir /r "$INSTDIR\core"
  RMDir /r "$INSTDIR\producteurs"
  RMDir /r "$INSTDIR\achats"
  RMDir /r "$INSTDIR\paiements"
  RMDir /r "$INSTDIR\stocks"
  RMDir /r "$INSTDIR\templates"
  RMDir /r "$INSTDIR\static"
  RMDir /r "$INSTDIR\staticfiles"
  Delete "$INSTDIR\*.bat"
  Delete "$INSTDIR\*.py"
  Delete "$INSTDIR\*.txt"
  Delete "$INSTDIR\*.md"
!macroend

Section "CacaoCoop" SecPrincipale
  SectionIn RO
  SetOutPath "$INSTDIR"
  !insertmacro SupprimerProgramme
  File /r /x "data" /x "sauvegardes" /x "__pycache__" "${SOURCE}\*.*"
  CreateDirectory "$INSTDIR\data"
  CreateDirectory "$INSTDIR\sauvegardes"

  WriteUninstaller "$INSTDIR\Desinstaller.exe"
  WriteRegStr HKCU "${CLE_DESINSTALLATION}" "DisplayName" "CacaoCoop"
  WriteRegStr HKCU "${CLE_DESINSTALLATION}" "DisplayVersion" "${VERSION}"
  WriteRegStr HKCU "${CLE_DESINSTALLATION}" "Publisher" "CacaoCoop"
  WriteRegStr HKCU "${CLE_DESINSTALLATION}" "DisplayIcon" "$INSTDIR\static\icones\icone.ico"
  WriteRegStr HKCU "${CLE_DESINSTALLATION}" "InstallLocation" "$INSTDIR"
  WriteRegStr HKCU "${CLE_DESINSTALLATION}" "UninstallString" '"$INSTDIR\Desinstaller.exe"'
  WriteRegDWORD HKCU "${CLE_DESINSTALLATION}" "NoModify" 1
  WriteRegDWORD HKCU "${CLE_DESINSTALLATION}" "NoRepair" 1

  ; Raccourcis : bureau et menu Démarrer.
  CreateShortcut "$DESKTOP\CacaoCoop.lnk" "$INSTDIR\CacaoCoop.bat" "" "$INSTDIR\static\icones\icone.ico"
  CreateDirectory "$SMPROGRAMS\CacaoCoop"
  CreateShortcut "$SMPROGRAMS\CacaoCoop\CacaoCoop.lnk" "$INSTDIR\CacaoCoop.bat" "" "$INSTDIR\static\icones\icone.ico"
  CreateShortcut "$SMPROGRAMS\CacaoCoop\CacaoCoop - réseau (tablettes).lnk" "$INSTDIR\CacaoCoop - reseau (tablettes).bat" "" "$INSTDIR\static\icones\icone.ico"
  CreateShortcut "$SMPROGRAMS\CacaoCoop\Sauvegarder les données.lnk" "$INSTDIR\Sauvegarder les donnees.bat"
  CreateShortcut "$SMPROGRAMS\CacaoCoop\Dossier des sauvegardes.lnk" "$INSTDIR\sauvegardes"
  CreateShortcut "$SMPROGRAMS\CacaoCoop\Guide d'installation.lnk" "$INSTDIR\GUIDE_INSTALLATION.txt"
  CreateShortcut "$SMPROGRAMS\CacaoCoop\Désinstaller CacaoCoop.lnk" "$INSTDIR\Desinstaller.exe"
SectionEnd

Section "Uninstall"
  !insertmacro SupprimerProgramme
  Delete "$INSTDIR\Desinstaller.exe"
  Delete "$DESKTOP\CacaoCoop.lnk"
  RMDir /r "$SMPROGRAMS\CacaoCoop"
  DeleteRegKey HKCU "${CLE_DESINSTALLATION}"
  ; Le dossier n'est supprimé que s'il est vide (données et sauvegardes conservées).
  RMDir "$INSTDIR\data"
  RMDir "$INSTDIR\sauvegardes"
  RMDir "$INSTDIR"
  IfFileExists "$INSTDIR\data\*.*" 0 +2
    MessageBox MB_OK|MB_ICONINFORMATION "CacaoCoop est désinstallé.$\r$\n$\r$\nVos données ont été conservées dans :$\r$\n$INSTDIR\data$\r$\n$INSTDIR\sauvegardes"
SectionEnd
