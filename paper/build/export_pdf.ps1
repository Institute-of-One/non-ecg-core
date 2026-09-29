$ErrorActionPreference = 'Stop'
$word = New-Object -ComObject Word.Application
try {
  $word.Visible = $false
  $word.DisplayAlerts = 0
  $word.Options.Pagination = $false
  $word.Options.CheckSpellingAsYouType = $false
  $word.Options.CheckGrammarAsYouType = $false
  $document = $word.Documents.Open('D:\DevGit\non-ecg_core\IORN-011\paper\build\manuscript_pmb.docx', $false, $true)
  $document.ExportAsFixedFormat('D:\DevGit\non-ecg_core\IORN-011\paper\build\PMB_manuscript.staged.pdf', 17)
  $document.Close(0)
} finally {
  $word.Quit()
}
