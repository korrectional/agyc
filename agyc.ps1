param(
    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]]$Arguments
)
python "$PSScriptRoot\agyc.py" @Arguments
