param ($pull_request)
Write-Host "Applying patch ${pull_request}"

git checkout trunk
Invoke-WebRequest https://patch-diff.githubusercontent.com/raw/apache/libcloud/pull/${pull_request}.patch -OutFile ${env:temp}/${pull_request}.patch
git am ${env:temp}/${pull_request}.patch
$last_message = git log -1 --pretty=%B
$new_message = $last_message+" Closes #${pull_request}"
git commit --amend -m "${new_message}"
