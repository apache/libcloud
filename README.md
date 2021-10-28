# Skip Duplicate Actions

`skip-duplicate-actions` provides the following features to optimize GitHub Actions:

- [Skip duplicate workflow-runs](#skip-duplicate-workflow-runs) after merges, pull requests or similar.
- [Skip concurrent or parallel workflow-runs](#skip-concurrent-workflow-runs) for things that you do not want to run twice.
- [Skip ignored paths](#skip-ignored-paths) to speedup documentation-changes or similar.
- [Skip if paths not changed](#skip-if-paths-not-changed) for something like directory-specific tests.
- [Cancel outdated workflow-runs](#cancel-outdated-workflow-runs) after branch-pushes.

All of those features help to save time and costs; especially for long-running workflows.
You can choose any subset of those features.

## Skip duplicate workflow-runs

If you work with feature branches, then you might see lots of _duplicate workflow-runs_.
For example, duplicate workflow-runs can happen if a workflow runs on a feature branch, but then the workflow is repeated right after merging the feature branch.
`skip-duplicate-actions` allows to prevent such runs.

- **Full traceability:** After clean merges, you will see a message like `Skip execution because the exact same files have been successfully checked in <previous_run_URL>`.
- **Fully configurable:** By default, manual triggers and cron will never be skipped.
- **Flexible Git usage:** `skip-duplicate-actions` does not care whether you use fast-forward-merges, rebase-merges or squash-merges.
  However, if a merge yields a result that is different from the source branch, then the resulting workflow-run will _not_ be skipped.
  This is commonly the case if you merge "outdated branches".

## Skip concurrent workflow-runs

Sometimes, there are workflows that you do not want to run twice at the same time even if they are triggered twice.
Therefore, `skip-duplicate-actions` provides the following options to skip a workflow-run if the same workflow is already running:

- **Always skip:** This is useful if you have a workflow that you never want to run twice at the same time.
- **Only skip same content:** For example, this can be useful if a workflow has both a `push` and a `pull_request` trigger, or if you push a tag right after pushing a commit.
- **Only skip newer runs with the same content:** If the same workflow is running on the exact same content, skip newer runs of it. `same_content_newer` ensures that at least one of those workflows will run, while `same_content` may skip all of them.
- **Only skip outdated runs:** For example, this can be useful for skip-checks that are not at the beginning of a job.
- **Never skip:** This disables the concurrent skipping functionality, but still lets you use all other options like duplicate skipping.

## Skip ignored paths

In many projects, it is unnecessary to run all tests for documentation-only-changes.
Therefore, GitHub provides a [paths-ignore](https://docs.github.com/en/actions/reference/workflow-syntax-for-github-actions#onpushpull_requestpaths) feature out of the box.
However, GitHub's `paths-ignore` has some limitations:

- GitHub's `paths-ignore` fails to look at previous commits. This means that the outcome depends on how often you push changes.
- Consequently, GitHub's `paths-ignore` does not work for [required checks](https://docs.github.com/en/github/administering-a-repository/about-required-status-checks).
  If you path-ignore a required check, then pull requests will block forever without being mergeable.

To overcome those limitations, `skip-duplicate-actions` provides a more flexible `paths_ignore`-feature with an efficient backtracking-algorithm.
Instead of stupidly looking at the current commit, `paths_ignore` will look for successful checks in your commit-history.

## Skip if paths not changed

In some projects, there are tasks that should be only executed if specific sub-directories were changed.
Therefore, GitHub provides a [paths](https://docs.github.com/en/actions/reference/workflow-syntax-for-github-actions#onpushpull_requestpaths) feature out of the box.
However, GitHub's `paths` has some limitations:

- GitHub's `paths` cannot skip individual steps in a workflow.
- GitHub's `paths` does not work with required checks that you really want to pass successfully.

To overcome those limitations, `skip-duplicate-actions` provides a more sophisticated `paths`-feature.
Instead of blindly skipping checks, the backtracking-algorithm will only skip something if it can find a suitable check in your commit-history.

## Cancel outdated workflow-runs

Typically, workflows should only run for the most recent commit.
Therefore, when you push changes to a branch, `skip-duplicate-actions` can be configured to cancel any previous workflow-runs that run against outdated commits.

- **Full traceability:** If a workflow-run is cancelled, then you will see a message like `Cancelled <previous_run_URL>`.
- **Guaranteed execution:** The cancellation-algorithm guarantees that a complete check-set will finish no matter what.

## Inputs

### `paths_ignore`

A JSON-array with ignored path-patterns, e.g. something like `'["**/README.md", "**/docs/**"]'`.
See [cheat sheet](https://docs.github.com/en/actions/reference/workflow-syntax-for-github-actions#filter-pattern-cheat-sheet) for path-pattern examples.
See [micromatch](https://github.com/micromatch/micromatch) for details about supported path-patterns.
Default `[]`.

### `paths`

A JSON-array with path-patterns, e.g. something like `'["platform-specific/**"]'`.
If this is non-empty, then `skip-duplicate-actions` will try to skip commits that did not change any of those paths.
It uses the same syntax as `paths_ignore`.
Default `[]`.

### `cancel_others`

If true, then workflow-runs from outdated commits will be cancelled. Default `false`.

### `skip_after_successful_duplicate`

If true, skip if an already finished duplicate run can be found. Default `true`.

### `do_not_skip`

A JSON-array with triggers that should never be skipped. Default `'["workflow_dispatch", "schedule"]'`.

### `concurrent_skipping`

One of `never`, `same_content`, `same_content_newer`, `outdated_runs`, `always`. Default `never`.

## Outputs

### `should_skip`

true if the current run should be skipped according to your configured rules. This should be evaluated for either individual steps or entire jobs.

## Usage examples

You can use `skip-duplicate-actions` to either skip individual steps or entire jobs.
To minimize changes to existing jobs, it is often easier to skip entire jobs.

### Option 1: Skip entire jobs

To skip entire jobs, you should add a `pre_job` that acts as a pre-condition for your `main_job`.
Although this example looks like a lot of code, there are only two additional lines in your project-specific `main_job` (the `needs`-clause and the `if`-clause):

```yml
jobs:
  pre_job:
    # continue-on-error: true # Uncomment once integration is finished
    runs-on: ubuntu-latest
    # Map a step output to a job output
    outputs:
      should_skip: ${{ steps.skip_check.outputs.should_skip }}
    steps:
      - id: skip_check
        uses: fkirc/skip-duplicate-actions@master
        with:
          # All of these options are optional, so you can remove them if you are happy with the defaults
          concurrent_skipping: 'never'
          skip_after_successful_duplicate: 'true'
          paths_ignore: '["**/README.md", "**/docs/**"]'
          do_not_skip: '["pull_request", "workflow_dispatch", "schedule"]'

  main_job:
    needs: pre_job
    if: ${{ needs.pre_job.outputs.should_skip != 'true' }}
    runs-on: ubuntu-latest
    steps:
      - run: echo "Running slow tests..." && sleep 30
```

### Option 2: Skip individual steps

The following example demonstrates how to skip an individual step with an `if`-clause and an `id`.
In this example, the step will be skipped if no files in `src/` or `dist/` were changed:

```yml
jobs:
  skip_individual_steps_job:
    runs-on: ubuntu-latest
    steps:
      - id: skip_check
        uses: fkirc/skip-duplicate-actions@master
        with:
          cancel_others: 'false'
          paths: '["src/**", "dist/**"]'
      - if: ${{ steps.skip_check.outputs.should_skip != 'true' }}
        run: |
          echo "Run only if src/ or dist/ changed..." && sleep 30
          echo "Do other stuff..."
```

## How does it work?

`skip-duplicate-actions` uses the [Workflow Runs API](https://docs.github.com/en/rest/reference/actions#workflow-runs) to query workflow-runs.
`skip-duplicate-actions` will only look at workflow-runs that belong to the same workflow as the current workflow-run.
After querying such workflow-runs, it will compare them with the current workflow-run as follows:

- If there exists a workflow-runs with the same tree hash, then we have identified a duplicate workflow-run.
- If there exists an in-progress workflow-run, then we can cancel it or skip, depending on your configuration.

## How does path-skipping work?

As mentioned above, `skip-duplicate-actions` provides a path-skipping functionality that is somewhat similar to GitHub's native `paths` and `paths_ignore` functionality.
However, path-skipping is not entirely trivial because there exist multiple options on how to do path-skipping.
Depending on your project, you might want to choose one of the following options:

### Option 1: Only look at the "current" commit

This is the thing that GitHub is currently doing, and I consider it as insufficient because it doesn't work for "required" checks.
Another problem is that the outcomes can be heavily dependent on which commits were pushed at which time, instead of the actual content that was pushed.

### Option 2: Look at Pull-Request-diffs

This option is probably implemented by https://github.com/dorny/paths-filter.
PR-diffs are simple to understand, but not everyone is using PRs for everything, so this is not an option for everyone.

### Option 3: Look for successful checks of previous commits

This is my personal favorite option and this is implemented by `skip-duplicate-actions`.
An advantage is that this works regardless of whether you are using PRs or feature-branches, and of course it also works for "required" checks.
Internally, `skip-duplicate-actions` uses the [Repos Commit API](https://docs.github.com/en/rest/reference/repos#get-a-commit) to perform an efficient backtracking-algorithm for paths-skipping-detection.

## Related Projects

GitHub is not the only thing that should be optimized.
Try `attranslate` if you need to translate websites or apps: https://github.com/fkirc/attranslate
