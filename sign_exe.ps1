
$thumb = "9364A9EA4FE16CE16DD5180A4A1131181B323D16"
$cert = Get-ChildItem Cert:/CurrentUser/My | Where-Object { $_.Thumbprint -eq $thumb }
if (-not $cert) { "CERT_NOT_FOUND" | Out-File "C:/DyberPet/_signresult.txt" -Encoding ascii; exit }
$exe = "C:/Users/76215/Desktop/六一桌宠_Setup.exe"
$r = @()
try {
  $s = Set-AuthenticodeSignature -FilePath $exe -Certificate $cert -TimestampServer "http://timestamp.digicert.com" -HashAlgorithm SHA256 -ErrorAction Stop
  $r += ("sign_status=" + $s.Status)
} catch {
  $r += ("ts_failed: " + $_.Exception.Message)
  $s = Set-AuthenticodeSignature -FilePath $exe -Certificate $cert -HashAlgorithm SHA256
  $r += ("sign_status2=" + $s.Status)
}
$r += ("subject=" + $cert.Subject)
$r | Out-File "C:/DyberPet/_signresult.txt" -Encoding utf8
$r
