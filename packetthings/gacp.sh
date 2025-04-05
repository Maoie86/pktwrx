#! /bin/bash
# https://terracoders.com/blog/git-add-commit-and-push-all-once-bash-function
# git add, commit and push all at the same time.

function addcommitpush () {

#wrap inline var in single quotes and store in var called message
message=\'"$@"\'
#git add and pass message var to git commit
git add -A && git commit -a -m "$message"

git push origin master

}
#pass inline variable to function and run
addcommitpush $1


