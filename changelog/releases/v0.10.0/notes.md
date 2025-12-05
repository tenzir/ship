This release adds support for reading changelog entry descriptions from files or stdin, making it easier to integrate with automated workflows and pipelines.

## 🚀 Features

### Add --description-file option to add command

**Component:** `cli`

The `add` command now accepts `--description-file` to read description content from a file. Use `-` to read from stdin, enabling piped input workflows.

*By @mavam.*
