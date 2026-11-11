; Installateur Windows de Akagri (NSIS 3).
; Construit par : python outils/construire_portable.py --installateur
; Source : le dossier portable dist/Akagri (Python embarqué + application).

Unicode true
!include "MUI2.nsh"

!ifndef VERSION
  !define VERSION "1.0.0"
!endif
!ifndef SOURCE
  !define SOURCE "..\dist\Akagri"
!endif
!ifndef SORTIE
  !define SORTIE "..\dist\Installer-Akagri.exe"
!endif

!define NOM "Akagri"
!define CLE_DESINSTALLATION "Software\Microsoft\Windows\CurrentVersion\Uninstall\Akagri"

Name "${NOM}"
OutFile "${SORTIE}"
; Installation dans le profil de l'utilisateur : aucun droit administrateur, et le dossier des données reste modifiable.
InstallDir "$LOCALAPPDATA\Akagri"
InstallDirRegKey HKCU "${CLE_DESINSTALLATION}" "InstallLocation"
RequestExecutionLevel user
SetCompressor /SOLID lzma
BrandingText "Akagri ${VERSION}"
VIProductVersion "${VERSION}.0"
VIAddVersionKey "ProductName" "Akagri"
VIAddVersionKey "FileDescription" "Gestion des achats et de la collecte de cacao"
VIAddVersionKey "FileVersion" "${VERSION}"
VIAddVersionKey "ProductVersion" "${VERSION}"
VIAddVersionKey "LegalCopyright" "Akagri"

!define MUI_ICON "${SOURCE}\static\icones\icone.ico"
!define MUI_UNICON "${SOURCE}\static\icones\icone.ico"
!define MUI_WELCOMEPAGE_TITLE "Installation de Akagri ${VERSION}"
!define MUI_WELCOMEPAGE_TEXT "Ce programme va installer Akagri, le logiciel de gestion des achats et de la collecte de cacao.$\r$\n$\r$\nSi Akagri est déjà installé, il sera mis à jour : vos données sont conservées. Pensez à faire une sauvegarde avant.$\r$\n$\r$\nFermez Akagri s'il est ouvert, puis cliquez sur Suivant."
!define MUI_FINISHPAGE_RUN "$INSTDIR\Akagri.bat"
!define MUI_FINISHPAGE_RUN_TEXT "Démarrer Akagri maintenant"
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

Section "Akagri" SecPrincipale
  SectionIn RO
  SetOutPath "$INSTDIR"
  !insertmacro SupprimerProgramme
  File /r /x "data" /x "sauvegardes" /x "__pycache__" "${SOURCE}\*.*"
  CreateDirectory "$INSTDIR\data"
  CreateDirectory "$INSTDIR\sauvegardes"

  WriteUninstaller "$INSTDIR\Desinstaller.exe"
  WriteRegStr HKCU "${CLE_DESINSTALLATION}" "DisplayName" "Akagri"
  WriteRegStr HKCU "${CLE_DESINSTALLATION}" "DisplayVersion" "${VERSION}"
  WriteRegStr HKCU "${CLE_DESINSTALLATION}" "Publisher" "Akagri"
  WriteRegStr HKCU "${CLE_DESINSTALLATION}" "DisplayIcon" "$INSTDIR\static\icones\icone.ico"
  WriteRegStr HKCU "${CLE_DESINSTALLATION}" "InstallLocation" "$INSTDIR"
  WriteRegStr HKCU "${CLE_DESINSTALLATION}" "UninstallString" '"$INSTDIR\Desinstaller.exe"'
  WriteRegDWORD HKCU "${CLE_DESINSTALLATION}" "NoModify" 1
  WriteRegDWORD HKCU "${CLE_DESINSTALLATION}" "NoRepair" 1

  ; Raccourcis : bureau et menu Démarrer.
  CreateShortcut "$DESKTOP\Akagri.lnk" "$INSTDIR\Akagri.bat" "" "$INSTDIR\static\icones\icone.ico"
  CreateDirectory "$SMPROGRAMS\Akagri"
  CreateShortcut "$SMPROGRAMS\Akagri\Akagri.lnk" "$INSTDIR\Akagri.bat" "" "$INSTDIR\static\icones\icone.ico"
  CreateShortcut "$SMPROGRAMS\Akagri\Akagri - réseau (tablettes).lnk" "$INSTDIR\Akagri - reseau (tablettes).bat" "" "$INSTDIR\static\icones\icone.ico"
  CreateShortcut "$SMPROGRAMS\Akagri\Sauvegarder les données.lnk" "$INSTDIR\Sauvegarder les donnees.bat"
  CreateShortcut "$SMPROGRAMS\Akagri\Dossier des sauvegardes.lnk" "$INSTDIR\sauvegardes"
  CreateShortcut "$SMPROGRAMS\Akagri\Guide d'installation.lnk" "$INSTDIR\GUIDE_INSTALLATION.txt"
  CreateShortcut "$SMPROGRAMS\Akagri\Désinstaller Akagri.lnk" "$INSTDIR\Desinstaller.exe"
SectionEnd

Section "Uninstall"
  !insertmacro SupprimerProgramme
  Delete "$INSTDIR\Desinstaller.exe"
  Delete "$DESKTOP\Akagri.lnk"
  RMDir /r "$SMPROGRAMS\Akagri"
  DeleteRegKey HKCU "${CLE_DESINSTALLATION}"
  ; Le dossier n'est supprimé que s'il est vide (données et sauvegardes conservées).
  RMDir "$INSTDIR\data"
  RMDir "$INSTDIR\sauvegardes"
  RMDir "$INSTDIR"
  IfFileExists "$INSTDIR\data\*.*" 0 +2
    MessageBox MB_OK|MB_ICONINFORMATION "Akagri est désinstallé.$\r$\n$\r$\nVos données ont été conservées dans :$\r$\n$INSTDIR\data$\r$\n$INSTDIR\sauvegardes" /SD IDOK
SectionEnd
