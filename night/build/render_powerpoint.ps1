param([string]$InputDeck, [string]$OutputFolder, [switch]$Pdf)
$ErrorActionPreference = 'Stop'
$workspacePath = 'D:\ALL\WK\Batcamp\night'
$outputFull = [IO.Path]::GetFullPath($OutputFolder)
if (!$outputFull.StartsWith($workspacePath + '\', [StringComparison]::OrdinalIgnoreCase)) { throw 'Output must be in night' }
New-Item -ItemType Directory -Path $outputFull -Force | Out-Null
$powerpoint = New-Object -ComObject PowerPoint.Application
$deck = $null
try {
    $deck = $powerpoint.Presentations.Open([IO.Path]::GetFullPath($InputDeck), -1, 0, 0)
    $deck.Export($outputFull, 'PNG', 1600, 900)
    if ($Pdf) { $deck.SaveAs((Join-Path $outputFull 'presentation.pdf'), 32) }
    $receipt = [pscustomobject]@{application='Microsoft PowerPoint COM'; input=[IO.Path]::GetFullPath($InputDeck); input_sha256=(Get-FileHash -LiteralPath $InputDeck -Algorithm SHA256).Hash.ToLowerInvariant(); opened_read_only=$true; native_open_verified=$true; slides=$deck.Slides.Count; width=$deck.PageSetup.SlideWidth; height=$deck.PageSetup.SlideHeight; png_export_succeeded=$true; pdf_export_succeeded=[bool]$Pdf; output=$outputFull; completed_utc=[DateTime]::UtcNow.ToString('o')}
    $receipt | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $outputFull 'powerpoint_render.json') -Encoding UTF8
    $receipt | ConvertTo-Json
} finally {
    if ($null -ne $deck) { $deck.Close(); [void][Runtime.InteropServices.Marshal]::ReleaseComObject($deck) }
    $powerpoint.Quit()
    [void][Runtime.InteropServices.Marshal]::ReleaseComObject($powerpoint)
}
