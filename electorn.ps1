param(
    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]]$ArgsList
)

python -m electorn.cli @ArgsList
