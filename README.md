# Likianta Flavored Formatter

`lkfmt` (Likianta flavored formatter) is an integration of `black` + `isort` +
`autoflake` with pre-defined settings to reformat my Python script code.

## Features

- `black` + `isort` + `autoflake` integration
- out-of-box settings
- one command to drive
- additional format styles by lk-flavor (*work in progress*)
    - keep indents on empty lines
    - keep newline at end of file
    - merge one-line `if`/`for` statements
    - align `:` in dict key-value pairs
    - align `=` in multi-line assignments
    - tweak `black` styles to balance the visual weight to ease your eyes
    - use `# nofmt` to skip formatting (like `# noqa`)
