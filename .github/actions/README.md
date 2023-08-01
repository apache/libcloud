# Vendored / Bundled Actions

ASF doesn't allow referencing 3rd party Github Actions inside the workflows so
we vendor 3rd party actions we use directly in this directory.

Those action repositories are stored using github subtrees and you can update them
using the following commands:

```bash
# Those commands need to run from the repository root
git subtree pull --prefix .github/actions/gh-action-pip-audit/ https://github.com/pypa/gh-action-pip-audit.git main --squash
```
