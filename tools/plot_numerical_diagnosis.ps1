param([Parameter(Mandatory=$true)][string]$DataPath, [Parameter(Mandatory=$true)][string]$OutputDirectory)
$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName System.Windows.Forms.DataVisualization
Add-Type -AssemblyName System.Drawing
$plotDescriptions = Get-Content -LiteralPath $DataPath -Encoding UTF8 -Raw | ConvertFrom-Json
foreach ($description in $plotDescriptions) {
    $chart = New-Object System.Windows.Forms.DataVisualization.Charting.Chart
    try {
        $chart.Width = 1500
        $chart.Height = 400 * $description.panels.Count + 140
        $chart.BackColor = [System.Drawing.Color]::White
        $chart.AntiAliasing = 'All'
        $title = $chart.Titles.Add([string]$description.title)
        $title.Font = New-Object System.Drawing.Font('Arial', 16)
        $legend = $chart.Legends.Add('legend')
        $legend.Docking = 'Bottom'
        $legend.Font = New-Object System.Drawing.Font('Arial', 10)
        $panelIndex = 0
        foreach ($panel in $description.panels) {
            $areaName = 'panel' + $panelIndex
            $area = $chart.ChartAreas.Add($areaName)
            $area.Position = New-Object System.Windows.Forms.DataVisualization.Charting.ElementPosition(2, (8 + 78 * $panelIndex / $description.panels.Count), 96, (78 / $description.panels.Count))
            $area.AxisX.Title = 'Time [s]'
            $area.AxisY.Title = [string]$panel.y_label
            $area.AxisX.Minimum = [double]$panel.x_min
            $area.AxisX.Maximum = [double]$panel.x_max
            $area.AxisX.Interval = if ($panel.x_max - $panel.x_min -lt 0.12) { 0.01 } else { 0.05 }
            $area.AxisX.LabelStyle.Format = '0.00'
            $area.AxisY.Minimum = 0
            $area.AxisX.MajorGrid.LineColor = [System.Drawing.Color]::Gainsboro
            $area.AxisY.MajorGrid.LineColor = [System.Drawing.Color]::Gainsboro
            $area.AxisX.TitleFont = New-Object System.Drawing.Font('Arial', 11)
            $area.AxisY.TitleFont = New-Object System.Drawing.Font('Arial', 11)
            $holdingBand = New-Object System.Windows.Forms.DataVisualization.Charting.StripLine
            $holdingBand.IntervalOffset = 0.30
            $holdingBand.StripWidth = 0.05
            $holdingBand.BackColor = [System.Drawing.Color]::FromArgb(28, 80, 130, 90)
            $area.AxisX.StripLines.Add($holdingBand)
            foreach ($curve in $panel.series) {
                $item = $chart.Series.Add($areaName + ' ' + [string]$curve.name)
                $item.ChartArea = $areaName
                $item.LegendText = [string]$curve.name
                $item.ChartType = 'Line'
                $item.BorderWidth = 3
                $item.Color = [System.Drawing.Color]::FromName([string]$curve.color)
                if ($curve.name -like 'IE *nodes') { $item.MarkerStyle = 'Circle'; $item.MarkerSize = 5 }
                if ($curve.name -like '*limit') { $item.BorderDashStyle = 'Dash' }
                foreach ($point in $curve.points) {
                    if ([double]$point[0] -ge [double]$panel.x_min - 1e-10 -and [double]$point[0] -le [double]$panel.x_max + 1e-10) {
                        [void]$item.Points.AddXY([double]$point[0], [double]$point[1])
                    }
                }
            }
            $panelIndex++
        }
        $outputPath = Join-Path -Path $OutputDirectory -ChildPath ([string]$description.filename)
        $chart.SaveImage($outputPath, 'Png')
    } finally {
        $chart.Dispose()
    }
}
