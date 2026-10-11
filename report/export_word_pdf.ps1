param([string]$DocxPath,[string]$PdfPath)
# Dedicated Word COM instance: does not close or alter the user's Word documents.
$reportWord = $null
$reportDocument = $null
try {
    $reportWord = New-Object -ComObject Word.Application
    $reportWord.Visible = $false
    $reportWord.DisplayAlerts = 0
    $reportWord.AutomationSecurity = 3
    $reportDocument = $reportWord.Documents.Open($DocxPath, $false, $true)
    $reportDocument.ExportAsFixedFormat($PdfPath, 17)
    Write-Output "Exported report PDF using Microsoft Word."
} finally {
    if ($reportDocument) { $reportDocument.Close(0); [void][System.Runtime.InteropServices.Marshal]::ReleaseComObject($reportDocument) }
    if ($reportWord) { $reportWord.Quit(); [void][System.Runtime.InteropServices.Marshal]::ReleaseComObject($reportWord) }
}
