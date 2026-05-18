param(
    [Parameter(Mandatory = $true)]
    [string]$Changelog,

    [string]$Output = "",
    [switch]$Force
)

$scriptPath = Join-Path $PSScriptRoot "translate_changelog_deepl.py"
$argsList = @($scriptPath, $Changelog)

if ($Output) {
    $argsList += @("--output", $Output)
}

if ($Force) {
    $argsList += "--force"
}

python @argsList
