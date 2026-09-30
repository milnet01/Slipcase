# Build dist\Slipcase-windows-x64.exe and run its self-check (SLIP-0019).
#
# .github/workflows/release.yml runs this same script, so a build made on a
# Windows machine by hand and the one attached to a release are made the same
# way.
#
# Usage: powershell -ExecutionPolicy Bypass -File scripts\build-windows.ps1
#   $env:PYTHON              interpreter to build with (default: python)
#   $env:SLIPCASE_BUILD_DIR  scratch folder (default: build\ in the repository)
$ErrorActionPreference = "Stop"

Set-Location (Split-Path $PSScriptRoot -Parent)

$python = if ($env:PYTHON) { $env:PYTHON } else { "python" }
$build = if ($env:SLIPCASE_BUILD_DIR) { $env:SLIPCASE_BUILD_DIR } else { "build" }
$name = "Slipcase-windows-x64.exe"

function Assert-Ok($what) {
    if ($LASTEXITCODE -ne 0) { throw "$what failed with exit code $LASTEXITCODE" }
}

Write-Host "`n=== bundle ==="
& $python -m venv "$build\venv"; Assert-Ok "creating the build environment"
& "$build\venv\Scripts\python.exe" -m pip install --quiet --disable-pip-version-check `
    -r requirements.lock -r requirements-build.txt; Assert-Ok "installing the dependencies"
& "$build\venv\Scripts\pyinstaller.exe" --noconfirm --log-level WARN `
    --distpath dist --workpath "$build\work" packaging\slipcase.spec; Assert-Ok "bundling"

Write-Host "`n=== self-check ==="
# A private settings folder, and no window: the check must not touch the
# settings of whoever runs the build. The report file is the evidence. The
# build has no console, and Start-Process does not reliably hand back an exit
# code, so neither of those is.
$smoke = Join-Path ([IO.Path]::GetTempPath()) ("slipcase-smoke-" + [guid]::NewGuid())
New-Item -ItemType Directory -Path $smoke | Out-Null
try {
    $env:XDG_CONFIG_HOME = $smoke
    $env:QT_QPA_PLATFORM = "offscreen"
    $run = Start-Process -FilePath "dist\$name" -ArgumentList "--smoke=$smoke\report.txt" -PassThru
    if (-not $run.WaitForExit(300000)) {
        $run.Kill()
        throw "the self-check did not finish within five minutes"
    }
    if (-not (Test-Path "$smoke\report.txt")) { throw "the self-check wrote no report" }
    $report = (Get-Content "$smoke\report.txt" -Raw).Trim()
    Write-Host $report
    if ($report -notmatch '^slipcase smoke OK ') { throw "the self-check failed" }
}
finally {
    Remove-Item -Recurse -Force $smoke -ErrorAction SilentlyContinue
}

$hash = (Get-FileHash "dist\$name" -Algorithm SHA256).Hash.ToLower()
# ASCII with a bare newline, the form `sha256sum --check` reads.
[IO.File]::WriteAllText("$PWD\dist\$name.sha256", "$hash  $name`n")
$size = [math]::Round((Get-Item "dist\$name").Length / 1MB)
Write-Host "`nbuilt dist\$name ($size MB)"
