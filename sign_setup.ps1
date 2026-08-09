
$ErrorActionPreference = "Stop"
$log = "C:/DyberPet/_signlog.txt"
"" | Out-File -FilePath $log -Encoding utf8
function Log($m){ Add-Content -Path $log -Value $m }

$cn = "CN=爱小瑾的小选"
Log "step1: ensure code-signing cert in CurrentUser\My"
$existing = Get-ChildItem Cert:/CurrentUser/My | Where-Object { $_.Subject -like '*爱小瑾*' -and ($_.EnhancedKeyUsageList -match 'Code Signing') }
if ($existing) { $cert = $existing[0]; Log ("found thumb=" + $cert.Thumbprint) }
else { $cert = New-SelfSignedCertificate -Subject $cn -Type CodeSigningCert -CertStoreLocation Cert:/CurrentUser/My; Log ("created thumb=" + $cert.Thumbprint) }

Log "step2: import public key into CurrentUser\Root (so local UAC trusts it)"
$tmp = "C:/DyberPet/_pub.cer"
Export-Certificate -Cert $cert -FilePath $tmp | Out-Null
Import-Certificate -FilePath $tmp -CertStoreLocation Cert:/CurrentUser/Root | Out-Null
Remove-Item $tmp
Log "imported to CurrentUser\Root"

Log "step3: sign desktop installer exe"
$exe = "C:/Users/76215/Desktop/六一桌宠_Setup.exe"
if (Test-Path $exe) {
  try {
    $s = Set-AuthenticodeSignature -FilePath $exe -Certificate $cert -TimestampServer "http://timestamp.digicert.com"
    Log ("sign status=" + $s.Status)
  } catch {
    Log ("sign-with-ts failed: " + $_.Exception.Message + " -> retry without timestamp")
    $s = Set-AuthenticodeSignature -FilePath $exe -Certificate $cert
    Log ("sign status2=" + $s.Status)
  }
} else { Log "exe missing, skip sign" }
Log "DONE"
