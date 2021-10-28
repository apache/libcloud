See https://github.com/marketplace/actions/skip-duplicate-actions for a list of non-breaking changes.

## Breaking changes from 2.X to 3

Set `concurrent_skipping` to one of the values that are described in the README,
or omit it if you do not want any concurrent skipping functionality.

## Breaking changes from 1.X to 2

If you used `skip_concurrent_trigger`, then you should replace it with something like the following line:

`do_not_skip: '["pull_request", "workflow_dispatch", "schedule"]'`
