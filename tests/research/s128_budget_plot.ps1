# Offline plot of derived CSV only; uses the installed Windows charting library.
$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName System.Windows.Forms.DataVisualization
$taskRoot = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '../..'))
$taskEvidence = Join-Path $taskRoot 'evidence/s128_budget'
$taskRows = Import-Csv -LiteralPath (Join-Path $taskEvidence 'evaluation_curve.csv')
$taskChart = New-Object System.Windows.Forms.DataVisualization.Charting.Chart
try {
    $taskChart.Width = 1400
    $taskChart.Height = 750
    $taskChart.BackColor = [Drawing.Color]::White
    $taskChart.AntiAliasing = 'All'
    $taskTitle = $taskChart.Titles.Add('S12.8: all 79 sealed physical evaluations')
    $taskTitle.Font = New-Object Drawing.Font('Segoe UI', 19)
    $taskArea = $taskChart.ChartAreas.Add('curve')
    $taskArea.AxisX.Title = 'Completed physical evaluation (700 physical steps each)'
    $taskArea.AxisX.Minimum = 0
    $taskArea.AxisX.Maximum = 80
    $taskArea.AxisX.Interval = 5
    $taskArea.AxisY.Title = 'Normalized constraint violation g (lower is better)'
    $taskArea.AxisY.Minimum = 0
    $taskArea.AxisY.Maximum = 22
    foreach ($taskAxis in @($taskArea.AxisX, $taskArea.AxisY)) {
        $taskAxis.MajorGrid.LineColor = [Drawing.Color]::FromArgb(225, 230, 235)
        $taskAxis.TitleFont = New-Object Drawing.Font('Segoe UI', 12)
        $taskAxis.LabelStyle.Font = New-Object Drawing.Font('Segoe UI', 11)
    }
    $taskBand = New-Object System.Windows.Forms.DataVisualization.Charting.StripLine
    $taskBand.IntervalOffset = 17.5
    $taskBand.StripWidth = 52
    $taskBand.BackColor = [Drawing.Color]::FromArgb(22, 30, 110, 190)
    $taskArea.AxisX.StripLines.Add($taskBand)
    $taskLegend = $taskChart.Legends.Add('legend')
    $taskLegend.Docking = 'Bottom'
    $taskLegend.Font = New-Object Drawing.Font('Segoe UI', 11)
    $taskActual = $taskChart.Series.Add('Evaluations including probes')
    $taskActual.ChartType = 'Point'
    $taskActual.MarkerSize = 6
    $taskActual.Color = [Drawing.Color]::Gray
    $taskBest = $taskChart.Series.Add('Best observed so far')
    $taskBest.ChartType = 'StepLine'
    $taskBest.BorderWidth = 3
    $taskBest.Color = [Drawing.Color]::FromArgb(20, 100, 175)
    $taskNmpc = $taskChart.Series.Add('NMPC evaluations')
    $taskNmpc.ChartType = 'Point'
    $taskNmpc.MarkerStyle = 'Diamond'
    $taskNmpc.MarkerSize = 11
    $taskNmpc.Color = [Drawing.Color]::FromArgb(205, 75, 30)
    foreach ($taskRow in $taskRows) {
        $taskN = [int]$taskRow.evaluation
        [void]$taskActual.Points.AddXY($taskN, [double]$taskRow.gap)
        $taskIndex = $taskBest.Points.AddXY($taskN, [double]$taskRow.best_gap)
        if ($taskN -in @(30, 43, 56, 69)) {
            $taskBest.Points[$taskIndex].Label = "#$taskN"
            $taskBest.Points[$taskIndex].Font = New-Object Drawing.Font('Segoe UI', 11)
        }
        if ($taskRow.method -eq 'nmpc') {
            [void]$taskNmpc.Points.AddXY($taskN, [double]$taskRow.gap)
        }
    }
    $taskNote = $taskChart.Titles.Add('Shaded region: H18 batch (#18-69); Agent received its feedback only after #69. No evaluation passed.')
    $taskNote.Docking = 'Bottom'
    $taskNote.Font = New-Object Drawing.Font('Segoe UI', 11)
    $taskChart.SaveImage((Join-Path $taskEvidence 'evaluation_curve.png'), 'Png')
} finally {
    $taskChart.Dispose()
}
