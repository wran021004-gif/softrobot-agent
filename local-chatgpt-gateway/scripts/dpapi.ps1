# Gateway adapter: no credentials in argv, environment variables or temporary files.
param([Parameter(Mandatory=$true)][ValidateSet('encrypt','decrypt','prepare')][string]$Action)
$ErrorActionPreference = 'Stop'
try {
    Add-Type -AssemblyName System.Security
    $payload = [Console]::In.ReadToEnd()
    if ($Action -eq 'prepare') {
        $stateDirectory = [System.IO.Path]::GetFullPath($payload)
        $sid = [System.Security.Principal.WindowsIdentity]::GetCurrent().User.Value
        $owner = New-Object System.Security.Principal.SecurityIdentifier($sid)
        $acl = New-Object System.Security.AccessControl.DirectorySecurity
        $acl.SetOwner($owner)
        $acl.SetAccessRuleProtection($true, $false)
        $rule = New-Object System.Security.AccessControl.FileSystemAccessRule($owner, 'FullControl', 'ContainerInherit, ObjectInherit', 'None', 'Allow')
        $acl.AddAccessRule($rule)
        [System.IO.Directory]::SetAccessControl($stateDirectory, $acl)
        [Console]::Out.Write('OK')
    } else {
        $bytes = [Convert]::FromBase64String($payload)
        $scope = [System.Security.Cryptography.DataProtectionScope]::CurrentUser
        if ($Action -eq 'encrypt') {
            $result = [System.Security.Cryptography.ProtectedData]::Protect($bytes, $null, $scope)
        } else {
            $result = [System.Security.Cryptography.ProtectedData]::Unprotect($bytes, $null, $scope)
        }
        [Console]::Out.Write([Convert]::ToBase64String($result))
        [Array]::Clear($bytes, 0, $bytes.Length)
        [Array]::Clear($result, 0, $result.Length)
    }
    exit 0
} catch {
    # Do not emit exception details: they can contain caller input.
    [Console]::Error.Write('Windows protected storage operation failed.')
    exit 1
}
