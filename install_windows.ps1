# Installs the Ethical Hacking Test for the current Windows user and puts an icon on the OneDrive desktop.
# Usage: powershell -ExecutionPolicy Bypass -File install_windows.ps1 [-SkipTests]
param([switch]$SkipTests)
$ErrorActionPreference = 'Continue'
$repoZip = 'https://github.com/hawpetossjustin25-collab/ethical-hacking-test/archive/refs/heads/main.zip'
$root = Join-Path $env:LOCALAPPDATA 'EthicalHackingTest'
$app = Join-Path $root 'app'

$py = (Get-ChildItem "$env:LOCALAPPDATA\Programs\Python\Python3*\python.exe" -ErrorAction SilentlyContinue |
       Sort-Object FullName -Descending | Select-Object -First 1).FullName
if (-not $py) { $py = (Get-Command python -ErrorAction SilentlyContinue).Source }
if (-not $py) { Write-Error 'Python 3 not found'; exit 1 }
$pyw = Join-Path (Split-Path $py) 'pythonw.exe'

New-Item -ItemType Directory -Force -Path $root | Out-Null
$zip = Join-Path $root 'src.zip'
Invoke-WebRequest -UseBasicParsing $repoZip -OutFile $zip
if (-not (Test-Path $zip)) { Write-Error 'download failed'; exit 1 }
$tmp = Join-Path $root 'extract'
Remove-Item -Recurse -Force $tmp -ErrorAction SilentlyContinue
Expand-Archive -Force $zip $tmp
Remove-Item -Recurse -Force $app -ErrorAction SilentlyContinue
Move-Item (Get-ChildItem $tmp | Select-Object -First 1).FullName $app
Remove-Item -Recurse -Force $tmp, $zip

& $py -m pip install --user --quiet --disable-pip-version-check PyQt6 pytest certifi 2>&1 | Out-Null
& $py -c "import PyQt6.QtWidgets, PyQt6.QtMultimedia"
if ($LASTEXITCODE -ne 0) { Write-Error 'PyQt6 install failed'; exit 1 }

if (-not $SkipTests) {
    Push-Location $app
    $env:QT_QPA_PLATFORM = 'offscreen'
    & $py -m pytest -q -p no:cacheprovider 2>&1 | Select-Object -Last 3
    $testExit = $LASTEXITCODE
    Remove-Item Env:QT_QPA_PLATFORM
    Pop-Location
    if ($testExit -ne 0) { Write-Error "tests failed ($testExit)"; exit 1 }
}

$desktop = Join-Path $env:OneDrive 'Desktop'
if (-not $env:OneDrive -or -not (Test-Path $desktop)) { $desktop = [Environment]::GetFolderPath('Desktop') }
$lnk = Join-Path $desktop 'Ethical Hacking Test.lnk'
$shell = New-Object -ComObject WScript.Shell
$s = $shell.CreateShortcut($lnk)
$s.TargetPath = $pyw
$s.Arguments = '-m ethical_hacking_test'
$s.WorkingDirectory = $app
$s.IconLocation = "$env:SystemRoot\System32\imageres.dll,77"
$s.Description = 'Ethical Hacking & Cybersecurity Practice Test'
$s.Save()
Write-Output "INSTALLED $app"
Write-Output "SHORTCUT $lnk"
