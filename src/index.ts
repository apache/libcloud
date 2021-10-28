import * as core from '@actions/core'
import * as github from '@actions/github'
import {
  ActionsGetWorkflowRunResponseData,
  ActionsListWorkflowRunsResponseData,
  ReposGetCommitResponseData
} from '@octokit/types'
const micromatch = require('micromatch');

type WorkflowRunStatus = 'queued' | 'in_progress' | 'completed'
type WorkflowRunConclusion = 'success' | 'failure' | 'neutral' | 'cancelled' | 'skipped' | 'timed_out'

const concurrentSkippingMap = {
  "always": null,
  "same_content": null,
  "same_content_newer": null,
  "outdated_runs": null,
  "never": null,
}
function getConcurrentSkippingOptions(): string[] {
  return Object.keys(concurrentSkippingMap);
}
type ConcurrentSkippingOption = keyof typeof concurrentSkippingMap;

interface WorkflowRun {
  event: WRunTrigger;
  treeHash: string;
  commitHash: string;
  status: WorkflowRunStatus;
  conclusion: WorkflowRunConclusion | null;
  html_url: string;
  branch: string | null;
  runId: number;
  workflowId: number;
  createdAt: string;
  runNumber: number;
}

type WRunTrigger =  "pull_request" | "push" | "workflow_dispatch" | "schedule";

interface WRunContext {
  repoOwner: string;
  repoName: string;
  currentRun: WorkflowRun;
  olderRuns: WorkflowRun[];
  allRuns: WorkflowRun[];
  octokit: any;
  pathsIgnore: string[];
  paths: string[];
  doNotSkip: WRunTrigger[];
  concurrentSkipping: ConcurrentSkippingOption;
}

function parseWorkflowRun(run: ActionsGetWorkflowRunResponseData): WorkflowRun {
  const treeHash = run.head_commit?.tree_id;
  if (!treeHash) {
    logFatal(`Could not find the tree hash of run ${run}`);
  }
  const workflowId = run.workflow_id;
  if (!workflowId) {
    logFatal(`Could not find the workflow id of run ${run}`);
  }
  return {
    event: run.event as WRunTrigger,
    treeHash,
    commitHash: run.head_sha,
    status: run.status as WorkflowRunStatus,
    conclusion: run.conclusion as WorkflowRunConclusion ?? null,
    html_url: run.html_url,
    branch: run.head_branch ?? null,
    runId: run.id,
    workflowId,
    createdAt: run.created_at,
    runNumber: run.run_number,
  }
}

function parseAllRuns(response: ActionsListWorkflowRunsResponseData): WorkflowRun[] {
  return response.workflow_runs.map((run) => parseWorkflowRun(run));
}

function parseOlderRuns(response: ActionsListWorkflowRunsResponseData, currentRun: WorkflowRun): WorkflowRun[] {
  const olderRuns = response.workflow_runs.filter((run) => {
    // Only consider older workflow-runs to prevent some nasty race conditions and edge cases.
    return new Date(run.created_at).getTime() < new Date(currentRun.createdAt).getTime();
  });
  return olderRuns.map((run) => parseWorkflowRun(run));
}

async function main() {
  const token = core.getInput('github_token', { required: true });
  if (!token) {
    logFatal("Did not find github_token");
  }
  const repo = github.context.repo;
  const repoOwner = repo?.owner;
  if (!repoOwner) {
    logFatal("Did not find the repo owner");
  }
  const repoName = repo?.repo;
  if (!repoName) {
    logFatal("Did not find the repo name");
  }
  const runId = github.context.runId;
  if (!runId) {
    logFatal("Did not find runId");
  }

  let context: WRunContext;
  try {
  const octokit = github.getOctokit(token);
  const { data: current_run } = await octokit.actions.getWorkflowRun({
    owner: repoOwner,
    repo: repoName,
    run_id: runId,
  });
  const currentRun = parseWorkflowRun(current_run);

  const { data } = await octokit.actions.listWorkflowRuns({
    owner: repoOwner,
    repo: repoName,
    workflow_id: currentRun.workflowId,
    per_page: 100,
  });
  context = {
    repoOwner,
    repoName,
    currentRun,
    olderRuns: parseOlderRuns(data, currentRun),
    allRuns: parseAllRuns(data),
    octokit,
    pathsIgnore: getStringArrayInput("paths_ignore"),
    paths: getStringArrayInput("paths"),
    doNotSkip: getStringArrayInput("do_not_skip") as WRunTrigger[],
    concurrentSkipping: getConcurrentSkippingInput("concurrent_skipping"),
  };
  } catch (e) {
    core.warning(e);
    core.warning(`Failed to fetch the required workflow information`);
    exitSuccess({shouldSkip: false});
  }

  const cancelOthers = getBooleanInput('cancel_others', false);
  if (cancelOthers) {
    await cancelOutdatedRuns(context);
  }
  if (context.doNotSkip.includes(context.currentRun.event)) {
    core.info(`Do not skip execution because the workflow was triggered with '${context.currentRun.event}'`);
    exitSuccess({ shouldSkip: false });
  }
  const skipAfterSuccessfulDuplicates = getBooleanInput('skip_after_successful_duplicate', true);
  if (skipAfterSuccessfulDuplicates) {
    detectSuccessfulDuplicateRuns(context);
  }
  if (context.concurrentSkipping !== "never") {
    detectConcurrentRuns(context);
  }
  if (context.paths.length >= 1 || context.pathsIgnore.length >= 1) {
    if (skipAfterSuccessfulDuplicates) {
      await backtracePathSkipping(context);
    } else {
      core.warning(`Ignore paths detection because 'skip_after_successful_duplicate' is set to false`);
    }
  }
  core.info("Do not skip execution because we did not find a transferable run");
  exitSuccess({ shouldSkip: false });
}

async function cancelOutdatedRuns(context: WRunContext) {
  const currentRun = context.currentRun;
  const cancelVictims = context.olderRuns.filter((run) => {
    if (run.status === 'completed') {
      return false;
    }
    return run.treeHash !== currentRun.treeHash && run.branch === currentRun.branch;
  });
  if (!cancelVictims.length) {
    return core.info(`Did not find other workflow-runs to be cancelled`);
  }
  for (const victim of cancelVictims) {
    await cancelWorkflowRun(victim, context)
  }
}

async function cancelWorkflowRun(run: WorkflowRun, context: WRunContext) {
  try {
    const res = await context.octokit.actions.cancelWorkflowRun({
      owner: context.repoOwner,
      repo: context.repoName,
      run_id: run.runId,
    });
    core.info(`Cancelled ${run.html_url} with response code ${res.status}`);
  } catch (e) {
    core.warning(e);
    core.warning(`Failed to cancel ${run.html_url}`);
  }
}

function detectSuccessfulDuplicateRuns(context: WRunContext) {
  const duplicateRuns = context.olderRuns.filter((run) => run.treeHash === context.currentRun.treeHash);
  const successfulDuplicate = duplicateRuns.find((run) => {
    return run.status === 'completed' && run.conclusion === 'success';
  });
  if (successfulDuplicate) {
    core.info(`Skip execution because the exact same files have been successfully checked in ${successfulDuplicate.html_url}`);
    exitSuccess({ shouldSkip: true });
  }
}

function detectConcurrentRuns(context: WRunContext) {
  const concurrentRuns: WorkflowRun[] = context.allRuns.filter((run) => {
    if (run.status === 'completed') {
      return false;
    }
    if (run.runId === context.currentRun.runId) {
      return false;
    }
    return true;
  });
  if (!concurrentRuns.length) {
    core.info(`Did not find any concurrent workflow-runs`);
    return;
  }
  if (context.concurrentSkipping === "always") {
    core.info(`Skip execution because another instance of the same workflow is already running in ${concurrentRuns[0].html_url}`);
    exitSuccess({ shouldSkip: true });
  } else if (context.concurrentSkipping === "outdated_runs") {
    const newerRun = concurrentRuns.find((run) => new Date(run.createdAt).getTime() > new Date(context.currentRun.createdAt).getTime());
    if (newerRun) {
      core.info(`Skip execution because a newer instance of the same workflow is running in ${newerRun.html_url}`);
      exitSuccess({ shouldSkip: true });
    }
  } else if (context.concurrentSkipping === "same_content") {
    const concurrentDuplicate = concurrentRuns.find((run) => run.treeHash === context.currentRun.treeHash);
    if (concurrentDuplicate) {
      core.info(`Skip execution because the exact same files are concurrently checked in ${concurrentDuplicate.html_url}`);
      exitSuccess({ shouldSkip: true });
    }
  } else if (context.concurrentSkipping === "same_content_newer") {
    const concurrentIsOlder = concurrentRuns.find((run) => (run.treeHash === context.currentRun.treeHash) && (run.runNumber < context.currentRun.runNumber));
    if (concurrentIsOlder) {
      core.info(`Skip execution because the exact same files are concurrently checked in older ${concurrentIsOlder.html_url}`);
      exitSuccess({ shouldSkip: true });
    }
  }
  core.info(`Did not find any skippable concurrent workflow-runs`);
}

async function backtracePathSkipping(context: WRunContext) {
  let commit: ReposGetCommitResponseData | null;
  let iterSha: string | null = context.currentRun.commitHash;
  let distanceToHEAD = 0;
  do {
    commit = await fetchCommitDetails(iterSha, context);
    if (!commit) {
      return;
    }
    iterSha = commit.parents?.length ? commit.parents[0]?.sha : null;

    exitIfSuccessfulRunExists(commit, context);

    if (distanceToHEAD++ >= 50) {
      // Should be never reached in practice; we expect that this loop aborts after 1-3 iterations.
      core.warning(`Aborted commit-backtracing due to bad performance - Did you push an excessive number of ignored-path-commits?`);
      return;
    }
  } while (isCommitSkippable(commit, context));
}

function exitIfSuccessfulRunExists(commit: ReposGetCommitResponseData, context: WRunContext) {
  const treeHash = commit.commit.tree.sha;
  const matchingRuns = context.olderRuns.filter((run) => run.treeHash === treeHash);
  const successfulRun = matchingRuns.find((run) => {
    return run.status === 'completed' && run.conclusion === 'success';
  });
  if (successfulRun) {
    core.info(`Skip execution because all changes since ${successfulRun.html_url} are in ignored or skipped paths`);
    exitSuccess({ shouldSkip: true });
  }
}

function isCommitSkippable(commit: ReposGetCommitResponseData, context: WRunContext): boolean {
  const changedFiles = commit.files.map((f) => f.filename);
  if (isCommitPathIgnored(commit, context)) {
    core.info(`Commit ${commit.html_url} is path-ignored: All of '${changedFiles}' match against patterns '${context.pathsIgnore}'`);
    return true;
  }
  if (isCommitPathSkipped(commit, context)) {
    core.info(`Commit ${commit.html_url} is path-skipped: None of '${changedFiles}' matches against patterns '${context.paths}'`);
    return true;
  }
  core.info(`Stop backtracking at commit ${commit.html_url} because '${changedFiles}' are not skippable against paths '${context.paths}' or paths_ignore '${context.pathsIgnore}'`);
  return false;
}

const globOptions = {
  dot: true, // Match dotfiles. Otherwise dotfiles are ignored unless a . is explicitly defined in the pattern.
};

function isCommitPathIgnored(commit: ReposGetCommitResponseData, context: WRunContext): boolean {
  if (!context.pathsIgnore.length) {
    return false;
  }
  // Skip if all changed files match against pathsIgnore.
  const changedFiles = commit.files.map((f) => f.filename);
  const notIgnoredPaths = micromatch.not(changedFiles, context.pathsIgnore,  globOptions);
  return notIgnoredPaths.length === 0;
}

function isCommitPathSkipped(commit: ReposGetCommitResponseData, context: WRunContext): boolean {
  if (!context.paths.length) {
    return false;
  }
  // Skip if none of the changed files matches against context.paths.
  const changedFiles = commit.files.map((f) => f.filename);
  const matchExists = micromatch.some(changedFiles, context.paths, globOptions);
  return !matchExists;
}

async function fetchCommitDetails(sha: string | null, context: WRunContext): Promise<ReposGetCommitResponseData | null> {
  if (!sha) {
    return null;
  }
  try {
    const res = await context.octokit.repos.getCommit({
      owner: context.repoOwner,
      repo: context.repoName,
      ref: sha,
    });
    //core.info(`Fetched ${res} with response code ${res.status}`);
    return res.data;
  } catch (e) {
    core.warning(e);
    core.warning(`Failed to retrieve commit ${sha}`);
    return null;
  }
}

function exitSuccess(args: { shouldSkip: boolean }): never {
  core.setOutput("should_skip", args.shouldSkip);
  return process.exit(0) as never;
}

function formatCliOptions(options: string[]): string {
  return `${options.map((o) => `"${o}"`).join(", ")}`;
}
function getConcurrentSkippingInput(name: string): ConcurrentSkippingOption {
  const rawInput = core.getInput(name, { required: true });
  if (rawInput.toLowerCase() === 'false') {
    return "never"; // Backwards-compat
  } else if (rawInput.toLowerCase() === 'true') {
    return "same_content"; // Backwards-compat
  }
  const options = getConcurrentSkippingOptions();
  if (options.includes(rawInput)) {
    return rawInput as ConcurrentSkippingOption;
  } else {
    logFatal(`'${name}' must be one of ${formatCliOptions(options)}`);
  }
}

function getBooleanInput(name: string, defaultValue: boolean): boolean {
  const rawInput = core.getInput(name, { required: false });
  if (!rawInput) {
    return defaultValue;
  }
  if (defaultValue) {
    return rawInput.toLowerCase() !== 'false';
  } else {
    return rawInput.toLowerCase() === 'true';
  }
}

function getStringArrayInput(name: string): string[] {
  const rawInput = core.getInput(name, { required: false });
  if (!rawInput) {
    return [];
  }
  try {
    const array = JSON.parse(rawInput);
    if (!Array.isArray(array)) {
      logFatal(`Input '${rawInput}' is not a JSON-array`);
    }
    array.forEach((e) => {
      if (typeof e !== "string") {
        logFatal(`Element '${e}' of input '${rawInput}' is not a string`);
      }
    });
    return array;
  } catch (e) {
    core.error(e);
    logFatal(`Input '${rawInput}' is not a valid JSON`);
  }
}

function logFatal(msg: string): never {
  core.setFailed(msg);
  return process.exit(1) as never;
}

main().catch((e) => {
  core.error(e);
  logFatal(e.message);
});
