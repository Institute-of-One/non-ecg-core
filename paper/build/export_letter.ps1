$ErrorActionPreference = 'Stop'
$word = New-Object -ComObject Word.Application
$word.Visible = $false
$word.DisplayAlerts = 0
$word.Options.Pagination = $false
$document = $word.Documents.Open('D:\DevGit\non-ecg_core\IORN-011\paper\build\cover_letter.docx', $false, $true)
$document.ExportAsFixedFormat('D:\DevGit\non-ecg_core\IORN-011\paper\build\PMB_cover_letter.pdf', 17)
$document.Close(0)
$word.Quit()
