import * as core from '@actions/core'
import * as github from '@actions/github'
import {getOctokitOptions, GitHub} from '@actions/github/lib/utils'
import {retry} from '@octokit/plugin-retry'
import type {Endpoints} from '@octokit/types'
import micromatch from 'micromatch'
import yaml from 'js-yaml'

// Register 'retry' plugin with default values
const Octokit = GitHub.plugin(retry)

type ApiWorkflowRun =
  Endpoints['GET /repos/{owner}/{repo}/actions/runs/{run_id}']['response']['data']
type ApiWorkflowRuns =
  Endpoints['GET /repos/{owner}/{repo}/actions/runs']['response']['data']['workflow_runs'][number]
type ApiCommit =
  Endpoints['GET /repos/{owner}/{repo}/commits/{ref}']['response']['data']

const workflowRunTriggerOptions = [
  'pull_request',
  'push',
  'workflow_dispatch',
  'schedule',
  'release'
] as const
type WorkflowRunTrigger = typeof workflowRunTriggerOptions[number]

type WorkflowRunStatus = 'queued' | 'in_progress' | 'completed'

type WorkflowRunConclusion =
  | 'success'
  | 'failure'
  | 'neutral'
  | 'cancelled'
  | 'skipped'
  | 'timed_out'

interface WorkflowRun {
  id: number
  runNumber: number
  event: WorkflowRunTrigger
  treeHash: string
  commitHash: string
  status: WorkflowRunStatus | null
  conclusion: WorkflowRunConclusion | null
  htmlUrl: string
  branch: string | null
  repo: string | null
  workflowId: number
  createdAt: string
}

type ChangedFiles = {sha: string; htmlUrl: string; changedFiles: string[]}[]

type PathsFilter = Record<
  string,
  {
    paths_ignore: string[]
    paths: string[]
    backtracking: boolean | number
  }
>

type PathsResult = Record<
  string,
  {
    should_skip: 'unknown' | boolean
    backtrack_count: number
    skipped_by?: WorkflowRun
    matched_files?: string[]
  }
>

const concurrentSkippingOptions = [
  'always',
  'same_content',
  'same_content_newer',
  'outdated_runs',
  'never'
] as const
type ConcurrentSkipping = typeof concurrentSkippingOptions[number]

type Inputs = {
  paths: string[]
  pathsIgnore: string[]
  pathsFilter: PathsFilter
  doNotSkip: WorkflowRunTrigger[]
  concurrentSkipping: ConcurrentSkipping
  cancelOthers: boolean
  skipAfterSuccessfulDuplicates: boolean
}

type Context = {
  repo: {owner: string; repo: string}
  octokit: InstanceType<typeof Octokit>
  currentRun: WorkflowRun
  allRuns: WorkflowRun[]
  olderRuns: WorkflowRun[]
}

class SkipDuplicateActions {
  inputs: Inputs
  context: Context
  globOptions = {
    dot: true // Match dotfiles. Otherwise dotfiles are ignored unless a "." is explicitly defined in the pattern.
  }

  constructor(inputs: Inputs, context: Context) {
    this.inputs = inputs
    this.context = context
  }

  async run(): Promise<void> {
    // Cancel outdated runs.
    if (this.inputs.cancelOthers) {
      await this.cancelOutdatedRuns()
    }

    // Abort early if current run has been triggered by an event that should never be skipped.
    if (this.inputs.doNotSkip.includes(this.context.currentRun.event)) {
      core.info(
        `Do not skip execution because the workflow was triggered with '${this.context.currentRun.event}'`
      )
      await exitSuccess({
        shouldSkip: false,
        reason: 'do_not_skip'
      })
    }

    // Skip on successful duplicate run.
    if (this.inputs.skipAfterSuccessfulDuplicates) {
      const successfulDuplicateRun = this.findSuccessfulDuplicateRun(
        this.context.currentRun.treeHash
      )
      if (successfulDuplicateRun) {
        core.info(
          `Skip execution because the exact same files have been successfully checked in run ${successfulDuplicateRun.htmlUrl}`
        )
        await exitSuccess({
          shouldSkip: true,
          reason: 'skip_after_successful_duplicate',
          skippedBy: successfulDuplicateRun
        })
      }
    }

    // Skip on concurrent runs.
    if (this.inputs.concurrentSkipping !== 'never') {
      const concurrentRun = this.detectConcurrentRuns()
      if (concurrentRun) {
        await exitSuccess({
          shouldSkip: true,
          reason: 'concurrent_skipping',
          skippedBy: concurrentRun
        })
      }
    }

    // Skip on path matches.
    if (
      this.inputs.paths.length >= 1 ||
      this.inputs.pathsIgnore.length >= 1 ||
      Object.keys(this.inputs.pathsFilter).length >= 1
    ) {
      const {changedFiles, pathsResult} = await this.backtracePathSkipping()
      await exitSuccess({
        shouldSkip:
          pathsResult.global.should_skip === 'unknown'
            ? false
            : pathsResult.global.should_skip,
        reason: 'paths',
        skippedBy: pathsResult.global.skipped_by,
        pathsResult,
        changedFiles
      })
    }

    // Do not skip otherwise.
    core.info(
      'Do not skip execution because we did not find a transferable run'
    )
    await exitSuccess({
      shouldSkip: false,
      reason: 'no_transferable_run'
    })
  }

  async cancelOutdatedRuns(): Promise<void> {
    const cancelVictims = this.context.olderRuns.filter(run => {
      // Only cancel runs which are not yet completed.
      if (run.status === 'completed') {
        return false
      }
      // Only cancel runs from same branch and repo (ignore pull request runs from remote repositories)
      // and not with same tree hash.
      // See https://github.com/fkirc/skip-duplicate-actions/pull/177.
      return (
        run.treeHash !== this.context.currentRun.treeHash &&
        run.branch === this.context.currentRun.branch &&
        run.repo === this.context.currentRun.repo
      )
    })
    if (!cancelVictims.length) {
      return core.info('Did not find other workflow runs to be cancelled')
    }
    for (const victim of cancelVictims) {
      try {
        const res = await this.context.octokit.rest.actions.cancelWorkflowRun({
          ...this.context.repo,
          run_id: victim.id
        })
        core.info(
          `Cancelled run ${victim.htmlUrl} with response code ${res.status}`
        )
      } catch (error) {
        if (error instanceof Error || typeof error === 'string') {
          core.warning(error)
        }
        core.warning(`Failed to cancel ${victim.htmlUrl}`)
      }
    }
  }

  findSuccessfulDuplicateRun(treeHash: string): WorkflowRun | undefined {
    return this.context.olderRuns.find(
      run =>
        run.treeHash === treeHash &&
        run.status === 'completed' &&
        run.conclusion === 'success'
    )
  }

  detectConcurrentRuns(): WorkflowRun | undefined {
    const concurrentRuns = this.context.allRuns.filter(
      run => run.status !== 'completed'
    )

    if (!concurrentRuns.length) {
      core.info('Did not find any concurrent workflow runs')
      return
    }
    if (this.inputs.concurrentSkipping === 'always') {
      core.info(
        `Skip execution because another instance of the same workflow is already running in ${concurrentRuns[0].htmlUrl}`
      )
      return concurrentRuns[0]
    } else if (this.inputs.concurrentSkipping === 'outdated_runs') {
      const newerRun = concurrentRuns.find(
        run =>
          new Date(run.createdAt).getTime() >
          new Date(this.context.currentRun.createdAt).getTime()
      )
      if (newerRun) {
        core.info(
          `Skip execution because a newer instance of the same workflow is running in ${newerRun.htmlUrl}`
        )
        return newerRun
      }
    } else if (this.inputs.concurrentSkipping === 'same_content') {
      const concurrentDuplicate = concurrentRuns.find(
        run => run.treeHash === this.context.currentRun.treeHash
      )
      if (concurrentDuplicate) {
        core.info(
          `Skip execution because the exact same files are concurrently checked in run ${concurrentDuplicate.htmlUrl}`
        )
        return concurrentDuplicate
      }
    } else if (this.inputs.concurrentSkipping === 'same_content_newer') {
      const concurrentIsOlder = concurrentRuns.find(
        run =>
          run.treeHash === this.context.currentRun.treeHash &&
          run.runNumber < this.context.currentRun.runNumber
      )
      if (concurrentIsOlder) {
        core.info(
          `Skip execution because the exact same files are concurrently checked in older run ${concurrentIsOlder.htmlUrl}`
        )
        return concurrentIsOlder
      }
    }
    core.info(`Did not find any concurrent workflow runs that justify skipping`)
  }

  async backtracePathSkipping(): Promise<{
    pathsResult: PathsResult
    changedFiles: ChangedFiles
  }> {
    let commit: ApiCommit | null
    let iterSha: string | null = this.context.currentRun.commitHash
    let distanceToHEAD = 0
    const allChangedFiles: ChangedFiles = []

    const pathsFilter: PathsFilter = {
      ...this.inputs.pathsFilter,
      global: {
        paths: this.inputs.paths,
        paths_ignore: this.inputs.pathsIgnore,
        backtracking: true
      }
    }

    const pathsResult: PathsResult = {}
    for (const name of Object.keys(pathsFilter)) {
      pathsResult[name] = {should_skip: 'unknown', backtrack_count: 0}
    }

    do {
      commit = await this.fetchCommitDetails(iterSha)
      if (!commit) {
        break
      }
      iterSha = commit.parents?.length ? commit.parents[0]?.sha : null
      const changedFiles = commit.files
        ? commit.files
            .map(file => file.filename)
            .filter(file => typeof file === 'string')
        : []
      allChangedFiles.push({
        sha: commit.sha,
        htmlUrl: commit.html_url,
        changedFiles
      })

      const successfulRun =
        (distanceToHEAD >= 1 &&
          this.findSuccessfulDuplicateRun(commit.commit.tree.sha)) ||
        undefined

      for (const [name, values] of Object.entries(pathsResult)) {
        // Only process paths where status has not yet been determined.
        if (values.should_skip !== 'unknown') continue

        // Skip if paths were ignorable or skippable until now and there is a successful run for the current commit.
        if (successfulRun) {
          pathsResult[name].should_skip = true
          pathsResult[name].skipped_by = successfulRun
          pathsResult[name].backtrack_count = distanceToHEAD
          core.info(
            `Skip '${name}' because all changes since run ${successfulRun.htmlUrl} are in ignored or skipped paths`
          )
          continue
        }

        // Check if backtracking limit has been reached.
        if (
          (pathsFilter[name].backtracking === false && distanceToHEAD === 1) ||
          pathsFilter[name].backtracking === distanceToHEAD
        ) {
          pathsResult[name].should_skip = false
          pathsResult[name].backtrack_count = distanceToHEAD
          core.info(
            `Stop backtracking for '${name}' because the defined limit has been reached`
          )
          continue
        }

        // Ignorable if all changed files match against ignored paths.
        if (
          this.isCommitPathsIgnored(
            changedFiles,
            pathsFilter[name].paths_ignore
          )
        ) {
          core.info(
            `Commit ${commit.html_url} is path-ignored for '${name}': All of '${changedFiles}' match against patterns '${pathsFilter[name].paths_ignore}'`
          )
          continue
        }

        // Skippable if none of the changed files matches against paths.
        if (pathsFilter[name].paths.length >= 1) {
          const matches = this.getCommitPathsMatches(
            changedFiles,
            pathsFilter[name].paths
          )
          if (matches.length === 0) {
            core.info(
              `Commit ${commit.html_url} is path-skipped for '${name}': None of '${changedFiles}' matches against patterns '${pathsFilter[name].paths}'`
            )
            continue
          } else {
            pathsResult[name].matched_files = matches
          }
        }

        // Not ignorable or skippable.
        pathsResult[name].should_skip = false
        pathsResult[name].backtrack_count = distanceToHEAD
        core.info(
          `Stop backtracking for '${name}' at commit ${commit.html_url} because '${changedFiles}' are not skippable against paths '${pathsFilter[name].paths}' or paths_ignore '${pathsFilter[name].paths_ignore}'`
        )
      }

      // Should be never reached in practice; we expect that this loop aborts after 1-3 iterations.
      if (distanceToHEAD++ >= 50) {
        core.warning(
          'Aborted commit-backtracing due to bad performance - Did you push an excessive number of ignored-path commits?'
        )
        break
      }
    } while (
      Object.keys(pathsResult).some(
        path => pathsResult[path].should_skip === 'unknown'
      )
    )

    return {pathsResult, changedFiles: allChangedFiles}
  }

  isCommitPathsIgnored(changedFiles: string[], pathsIgnore: string[]): boolean {
    if (pathsIgnore.length === 0) {
      return false
    }
    const notIgnoredPaths = micromatch.not(
      changedFiles,
      pathsIgnore,
      this.globOptions
    )
    return notIgnoredPaths.length === 0
  }

  getCommitPathsMatches(changedFiles: string[], paths: string[]): string[] {
    const matches = micromatch(changedFiles, paths, this.globOptions)
    return matches
  }

  async fetchCommitDetails(sha: string | null): Promise<ApiCommit | null> {
    if (!sha) {
      return null
    }
    try {
      return (
        await this.context.octokit.rest.repos.getCommit({
          ...this.context.repo,
          ref: sha
        })
      ).data
    } catch (error) {
      if (error instanceof Error || typeof error === 'string') {
        core.warning(error)
      }
      core.warning(`Failed to retrieve commit ${sha}`)
      return null
    }
  }
}

async function main(): Promise<void> {
  // Get and validate inputs.
  const token = core.getInput('github_token', {required: true})
  const inputs = {
    paths: getStringArrayInput('paths'),
    pathsIgnore: getStringArrayInput('paths_ignore'),
    pathsFilter: getPathsFilterInput('paths_filter'),
    doNotSkip: getDoNotSkipInput('do_not_skip'),
    concurrentSkipping: getConcurrentSkippingInput('concurrent_skipping'),
    cancelOthers: core.getBooleanInput('cancel_others'),
    skipAfterSuccessfulDuplicates: core.getBooleanInput(
      'skip_after_successful_duplicate'
    )
  }

  const repo = github.context.repo
  const octokit = new Octokit(getOctokitOptions(token))

  // Get and parse the current workflow run.
  let apiCurrentRun: ApiWorkflowRun = null as unknown as ApiWorkflowRun
  try {
    const res = await octokit.rest.actions.getWorkflowRun({
      ...repo,
      run_id: github.context.runId
    })
    apiCurrentRun = res.data
  } catch (error) {
    core.warning(error as string | Error)
    await exitSuccess({
      shouldSkip: false,
      reason: 'no_transferable_run'
    })
  }
  const currentTreeHash = apiCurrentRun.head_commit?.tree_id
  if (!currentTreeHash) {
    exitFail(`
        Could not find the tree hash of run ${apiCurrentRun.id} (Workflow ID: ${apiCurrentRun.workflow_id},
        Name: ${apiCurrentRun.name}, Head Branch: ${apiCurrentRun.head_branch}, Head SHA: ${apiCurrentRun.head_sha}).
        This might be a run associated with a headless or removed commit.
      `)
  }
  const currentRun = mapWorkflowRun(apiCurrentRun, currentTreeHash)

  // Fetch list of runs for current workflow.
  const {
    data: {workflow_runs: apiAllRuns}
  } = await octokit.rest.actions.listWorkflowRuns({
    ...repo,
    workflow_id: currentRun.workflowId,
    per_page: 100
  })

  // List with all workflow runs.
  const allRuns = []
  // List with older workflow runs only (used to prevent some nasty race conditions and edge cases).
  const olderRuns = []

  // Check and map all runs.
  for (const run of apiAllRuns) {
    // Filter out current run and runs that lack 'head_commit' (most likely runs associated with a headless or removed commit).
    // See https://github.com/fkirc/skip-duplicate-actions/pull/178.
    if (run.id !== currentRun.id && run.head_commit) {
      const mappedRun = mapWorkflowRun(run, run.head_commit.tree_id)
      // Add to list of all runs.
      allRuns.push(mappedRun)
      // Check if run can be added to list of older runs.
      if (
        new Date(mappedRun.createdAt).getTime() <
        new Date(currentRun.createdAt).getTime()
      ) {
        olderRuns.push(mappedRun)
      }
    }
  }

  const skipDuplicateActions = new SkipDuplicateActions(inputs, {
    repo,
    octokit,
    currentRun,
    allRuns,
    olderRuns
  })
  await skipDuplicateActions.run()
}

function mapWorkflowRun(
  run: ApiWorkflowRun | ApiWorkflowRuns,
  treeHash: string
): WorkflowRun {
  return {
    id: run.id,
    runNumber: run.run_number,
    event: run.event as WorkflowRunTrigger,
    treeHash,
    commitHash: run.head_sha,
    status: run.status as WorkflowRunStatus,
    conclusion: run.conclusion as WorkflowRunConclusion,
    htmlUrl: run.html_url,
    branch: run.head_branch,
    // Wrong type: 'head_repository' can be null (probably when repo has been removed)
    repo: run.head_repository?.full_name ?? null,
    workflowId: run.workflow_id,
    createdAt: run.created_at
  }
}

/** Set all outputs and exit the action. */
async function exitSuccess(args: {
  shouldSkip: boolean
  reason: string
  skippedBy?: WorkflowRun
  pathsResult?: PathsResult
  changedFiles?: ChangedFiles
}): Promise<never> {
  const summary = [
    '<h2><a href="https://github.com/fkirc/skip-duplicate-actions">Skip Duplicate Actions</a></h2>',
    '<table>',
    '<tr>',
    '<td>Should Skip</td>',
    `<td>${args.shouldSkip ? 'Yes' : 'No'} (<i>${args.shouldSkip}</i>)</td>`,
    '</tr>',
    '<tr>',
    '<td>Reason</td>',
    `<td><i>${args.reason}</i></td>`,
    '</tr>'
  ]
  if (args.skippedBy) {
    summary.push(
      '<tr>',
      '<td>Skipped By</td>',
      `<td><a href="${args.skippedBy.htmlUrl}">${args.skippedBy.runNumber}</a></td>`,
      '</tr>'
    )
  }
  if (args.pathsResult) {
    summary.push(
      '<tr>',
      '<td>Paths Result</td>',
      `<td><pre lang="json">${JSON.stringify(
        args.pathsResult,
        null,
        2
      )}</pre></td>`,
      '</tr>'
    )
  }
  if (args.changedFiles) {
    const changedFiles = args.changedFiles
      .map(
        commit =>
          `<a href="${commit.htmlUrl}">${commit.sha.substring(0, 7)}</a>:
          <ul>${commit.changedFiles
            .map(file => `<li>${file}</li>`)
            .join('')}</ul>`
      )
      .join('')
    summary.push(
      '<tr>',
      '<td>Changed Files</td>',
      `<td>${changedFiles}</td>`,
      '</tr>'
    )
  }
  summary.push('</table>')
  await core.summary.addRaw(summary.join('')).write()

  core.setOutput('should_skip', args.shouldSkip)
  core.setOutput('reason', args.reason)
  core.setOutput('skipped_by', args.skippedBy || {})
  core.setOutput('paths_result', args.pathsResult || {})
  core.setOutput(
    'changed_files',
    args.changedFiles?.map(commit => commit.changedFiles) || []
  )
  process.exit(0)
}

/** Immediately terminate the action with failing exit code. */
function exitFail(error: unknown): never {
  if (error instanceof Error || typeof error == 'string') {
    core.error(error)
  }
  process.exit(1)
}

function getStringArrayInput(name: string): string[] {
  const rawInput = core.getInput(name)
  if (!rawInput) {
    return []
  }
  try {
    const array = JSON.parse(rawInput)
    if (!Array.isArray(array)) {
      exitFail(`Input '${rawInput}' is not a JSON-array`)
    }
    for (const element of array) {
      if (typeof element !== 'string') {
        exitFail(`Element '${element}' of input '${rawInput}' is not a string`)
      }
    }
    return array
  } catch (error) {
    if (error instanceof Error || typeof error === 'string') {
      core.error(error)
    }
    exitFail(`Input '${rawInput}' is not a valid JSON`)
  }
}

function getDoNotSkipInput(name: string): WorkflowRunTrigger[] {
  const rawInput = core.getInput(name)
  if (!rawInput) {
    return []
  }
  try {
    const array = JSON.parse(rawInput)
    if (!Array.isArray(array)) {
      exitFail(`Input '${rawInput}' is not a JSON-array`)
    }
    for (const element of array) {
      if (!workflowRunTriggerOptions.includes(element as WorkflowRunTrigger)) {
        exitFail(
          `Elements in '${name}' must be one of ${workflowRunTriggerOptions
            .map(option => `"${option}"`)
            .join(', ')}`
        )
      }
    }
    return array
  } catch (error) {
    if (error instanceof Error || typeof error === 'string') {
      core.error(error)
    }
    exitFail(`Input '${rawInput}' is not a valid JSON`)
  }
}

function getConcurrentSkippingInput(name: string): ConcurrentSkipping {
  const rawInput = core.getInput(name, {required: true})
  if (rawInput.toLowerCase() === 'false') {
    return 'never' // Backwards-compat
  } else if (rawInput.toLowerCase() === 'true') {
    return 'same_content' // Backwards-compat
  }
  if (concurrentSkippingOptions.includes(rawInput as ConcurrentSkipping)) {
    return rawInput as ConcurrentSkipping
  } else {
    exitFail(
      `'${name}' must be one of ${concurrentSkippingOptions
        .map(option => `"${option}"`)
        .join(', ')}`
    )
  }
}

function getPathsFilterInput(name: string): PathsFilter {
  const rawInput = core.getInput(name)
  if (!rawInput) {
    return {}
  }
  try {
    const input = yaml.load(rawInput)
    // Assign default values to each entry
    const pathsFilter: PathsFilter = {}
    for (const [key, value] of Object.entries(
      input as Record<string, Partial<PathsFilter[string]>>
    )) {
      pathsFilter[key] = {
        paths: value.paths || [],
        paths_ignore: value.paths_ignore || [],
        backtracking: value.backtracking == null ? true : value.backtracking
      }
    }
    return pathsFilter
  } catch (error) {
    if (error instanceof Error || typeof error === 'string') {
      core.error(error)
    }
    exitFail(`Input '${rawInput}' is invalid`)
  }
}

main()
