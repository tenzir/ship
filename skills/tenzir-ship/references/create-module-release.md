# Create a module release

Use this workflow when a parent project features changelog **modules**:
self-contained changelog projects nested under an umbrella project. 

Releasing a parent project is a two-phase workflow:

1. Release all module projects.
2. Release the parent project.

Begin with discovering the modules from the parent project:

```sh
uvx tenzir-ship stats --json
```

Map changed files to module `path` values.

## 1. Release affected modules

Release each module independently as follows:

1. Change the working directory to the module directory
2. [Create a release](create-release.md) without providing `--root` to
   `tenzir-ship`.

## 2. Release parent project

After module releases are complete, create the parent release.

Module summaries aggregate automatically in parent release notes.
