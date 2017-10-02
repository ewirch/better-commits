#!/usr/bin/env bash

set -e

startRef=$1

# validate startRef
if !(git rev-parse --verify -q $startRef > /dev/null); then
	echo "ERROR: Invalid ref specified."
	echo "Usage: $0 COMMITISH-ID"
	echo " COMMITISH-ID      Commit ID, ref name, branch name, etc..."
	echo ""
	exit 1
fi

origHead=$(git rev-parse HEAD)

## save current head
git update-ref -m "Before format script" HEAD HEAD

git reset -q --mixed $startRef >/dev/null 2>&1
if [ $? -ne 0 ]; then
	echo "'git reset' failed. Look for 'Before format script' in output of 'git reflog' to restore you original state."
	exit 1
fi

echo ""
git log $startRef..$origHead --pretty=format:'%Cred%h%Creset %Cblue<%an>%Creset %C(yellow)%d%Creset %s' --abbrev-commit
echo ""
echo -e "Make sure the above commits are the ones you want to format. Switch to your IDE and format the changed files if the list is correct. Press ENTER when finished.\n\nPress ENTER without applying changes if you want to cancel now."
read

git reset -q --mixed $origHead >/dev/null 2>&1
if [ $? -ne 0 ]; then
	echo "'git reset' failed. Look for 'Before format script' in output of 'git reflog' to restore you original state."
	exit 1
fi

echo "You can verify and commit the format changes now."
