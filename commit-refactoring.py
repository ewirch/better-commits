#!/usr/bin/python
from subprocess import run, PIPE, CompletedProcess
from sys import stderr

DEBUG = False
commandList = []

def run_unchecked(command: [str], input_string=None) -> CompletedProcess:
    add_to_command_list(command)
    result = run(command, input=input_string, stdout=PIPE, stderr=PIPE, encoding="UTF-8")
    return result

def run_checked(command: [str], input_string=None) -> CompletedProcess:
    result = run_unchecked(command, input_string)
    if result.returncode > 1:
        print_command_fail_stack(result)
    return result


def add_to_command_list(command):
    command_string = " ".join(command)
    commandList.append(command_string)
    if DEBUG:
        print(command_string)


def print_command_fail_stack(result):
    print("Previous commands:", file=stderr)
    for command_string in commandList:
        print("   " + command_string, file=stderr)
    print(result.stdout, file=stderr)
    print(result.stderr, file=stderr)
    print("""
Get back your work:
 $ git reflog
Locate the "refactoring scrip backup line".
 $ git reset --hard abcdef
 $ git clean -f
 $ git stash apply --index
""")
    exit(1)


def create_unique_branch_name() -> str:
    counter = 0
    branch_name, result = verify_branch_name(counter)
    while not result.returncode:
        counter += 1
        branch_name, result = verify_branch_name(counter)
    return branch_name


def verify_branch_name(counter):
    branch_name = "tmp-branch-" + str(counter)
    result = run_unchecked(["git", "rev-parse", "--verify", branch_name])
    return branch_name, result


def verify_worktree_clean() -> bool:
    # Check if worktree is clean:
    #  dirty working tree or uncommitted changes:
    #   git diff-index --quiet HEAD --
    #    0 = no uncommitted changes
    #    1 = uncommitted changes
    #    >1 = error
    result = run_unchecked(["git", "diff-index", "--quiet", "HEAD"])
    if result.returncode == 1:
        return False
    # check for un-tracked un-ignored files, they will cause the un-stash to fail (if the stash contains them too)
    #   git ls-files --exclude-standard --others --error-unmatch -- .
    #    0 = un-tracked, un-ignored files
    #    1 = clean
    #    >1 = error
    result = run_unchecked(["git", "ls-files", "--exclude-standard", "--others", "--error-unmatch", "--", "."])
    if result.returncode == 0:
        return False
    return True


class StatusLine:
    def __init__(self):
        self.lineId = None
        self.status = None
        self.fileModeHead = None
        self.fileModeIndex = None
        self.fileModeWorkTree = None
        self.hashHead = None
        self.hashIndex = None
        self.path = None
        self.originalPath = None


def git_status() -> [StatusLine]:
    result = run_checked(['git', 'status', '--porcelain=2'])
    stats = []
    for line in result.stdout.splitlines():
        if line[0] == '1':
            # modified entries
            status = StatusLine()
            (
                status.lineId, status.status, status.subModuleState, status.fileModeHead, status.fileModeIndex,
                status.fileModeWorkTree, status.hashHead, status.hashIndex, status.path) = line.split(sep=" ")
            stats.append(status)
        if line[0] == '2':
            # renamed entries
            status = StatusLine()
            (
                status.lineId, status.status, status.subModuleState, status.fileModeHead, status.fileModeIndex,
                status.fileModeWorkTree, status.hashHead, status.hashIndex, status.renameScore, paths) = line.split(
                sep=" ")
            (status.path, status.originalPath) = paths.split(sep="\t")
            stats.append(status)
    return stats


def get_current_branch_name() -> str:
    result = run_checked(["git", "symbolic-ref", "HEAD"])
    # stdout contains line breaks. splitlines removes them.
    return result.stdout.splitlines()[0] if result else ""


def stash_changes():
    run_checked(['git', 'update-ref', '-m', "refactoring script backup", "HEAD", "HEAD"])
    run_checked(["git", "stash", "save", "-q", "--include-untracked", "refactoring script backup"])
    run_checked(["git", "stash", "apply", "-q", "--index"])
    run_checked(["git", "stash", "save", "-q", "--include-untracked"])


def collect_deleted_files():
    deleted = []
    for status in git_status():
        if status.status[1] == 'D':
            # each deleted entry
            deleted.append(status.path)
    return deleted


def unstash_changes(previous_branch: str):
    unique_branch_name = create_unique_branch_name()
    run_checked(["git", "stash", "branch", unique_branch_name])
    run_checked(["git", "symbolic-ref", "HEAD", previous_branch])
    run_checked(["git", "branch", "-d", unique_branch_name])


def update_refactored_files(before_states):
    after_states = git_status()
    for beforeState in before_states:
        for afterState in after_states:
            if beforeState.path == afterState.path and beforeState.hashHead != afterState.hashHead:
                # replace the indexed hash by the new head hash
                index_entry = f"{afterState.fileModeIndex} {afterState.hashHead} 0\t{afterState.path}"
                run_checked(["git", "update-index", "--index-info"], index_entry)


def detached_head():
    result = run_unchecked(["git", "symbolic-ref", "-q", "HEAD"])
    return result.returncode == 1


def main():
    if detached_head():
        print("""
You are in 'detached HEAD' state. This script uses branches to do it's work. Check out the branch you want to work on. 
""")
        exit(1)
    current_branch = get_current_branch_name()
    pre_change_state = git_status()
    stash_changes()

    input("Apply refactoring now and commit it. Press ENTER when finished.")

    while not verify_worktree_clean():
        print("""
Work tree is dirty. Did you forget to commit your refactoring?
If the work tree is not clean, unstashing of the previous changes might fail.
Commit or revert your changes, remove any untracked un-ignored files and press ENTER when finished.
""")
        input()

    unstash_changes(current_branch)
    update_refactored_files(pre_change_state)


main()
