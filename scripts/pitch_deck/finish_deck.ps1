# Finishes the KrishiVault pitch deck in PowerPoint itself (COM), then renders every slide to PNG.
# 1. Slide 1: the farmer video plays on entry; after it ends the caption and the evidence cards fade in.
# 2. Saves the deck, then exports slide PNGs for checking.
# Usage: powershell -File finish_deck.ps1 -Deck <deck.pptx> -PngDir <folder> -VideoSeconds <clip length>
param([Parameter(Mandatory)][string]$Deck, [Parameter(Mandatory)][string]$PngDir, [double]$VideoSeconds = 30)

$ErrorActionPreference = "Stop"
$Deck = (Resolve-Path $Deck).Path
New-Item -ItemType Directory -Force $PngDir | Out-Null
$PngDir = (Resolve-Path $PngDir).Path

$app = New-Object -ComObject PowerPoint.Application
try {
    $pres = $app.Presentations.Open($Deck, $false, $false, $false)   # read-write, no title, no window
    $s1 = $pres.Slides.Item(1)
    $seq = $s1.TimeLine.MainSequence
    while ($seq.Count -gt 0) { $seq.Item(1).Delete() }

    $video = $null
    foreach ($sh in $s1.Shapes) { if ($sh.Type -eq 16) { $video = $sh } }        # msoMedia
    if (-not $video) { throw "No video on slide 1" }
    try { $video.MediaFormat.Volume = 1.0 } catch { Write-Output "volume left as is: $_" }
    # play on entry: msoAnimEffectMediaPlay (83), trigger "with previous" (2) so it starts when the slide opens
    $play = $seq.AddEffect($video, 83, 0, 2)
    $play.Timing.TriggerDelayTime = 0
    $video.AnimationSettings.PlaySettings.PlayOnEntry = -1
    $video.AnimationSettings.PlaySettings.HideWhileNotPlaying = 0
    $video.AnimationSettings.PlaySettings.StopAfterSlides = 1

    # after the clip: the overlay and the caption fade in, then the evidence cards one by one
    # ("with previous" (2) and delays measured from the slide's start, when the clip starts)
    foreach ($name in @("Hook overlay", "Hook kicker", "Hook caption")) {
        $fx = $seq.AddEffect($s1.Shapes.Item($name), 10, 0, 2)
        $fx.Timing.Duration = 0.6
        $fx.Timing.TriggerDelayTime = $VideoSeconds + 0.3
    }
    for ($n = 1; $n -le 7; $n++) {
        $names = @()
        foreach ($sh in $s1.Shapes) { if ($sh.Name -like "Ev $n *") { $names += $sh.Name } }
        $group = $s1.Shapes.Range([string[]]$names).Group()
        $group.Name = "Evidence $n"
        $fx = $seq.AddEffect($group, 10, 0, 2)
        $fx.Timing.Duration = 0.5
        $fx.Timing.TriggerDelayTime = $VideoSeconds + 1.0 + 0.35 * ($n - 1)
    }

    # links to the live prototype: a click action on the shapes keeps their own text colour
    foreach ($pair in @(@(5, "Live demo card"), @(5, "Demo link"), @(5, "Demo details"), @(10, "Close link"))) {
        $shape = $pres.Slides.Item($pair[0]).Shapes.Item($pair[1])
        $shape.ActionSettings.Item(1).Action = 7                       # ppActionHyperlink
        $shape.ActionSettings.Item(1).Hyperlink.Address = "https://koryu.ninja/"
        $shape.ActionSettings.Item(1).Hyperlink.ScreenTip = "Open the KrishiVault prototype"
    }
    $pres.Save()

    Get-ChildItem $PngDir -Filter "slide-*.png" | Remove-Item -Force
    $i = 0
    foreach ($s in $pres.Slides) {
        $i++
        $s.Export((Join-Path $PngDir ("slide-{0:D2}.png" -f $i)), "PNG", 1600, 900)
    }
    $pres.Close()
    Write-Output "finished $Deck; exported $i slides to $PngDir"
}
finally {
    $app.Quit()
    [System.Runtime.InteropServices.Marshal]::ReleaseComObject($app) | Out-Null
}
