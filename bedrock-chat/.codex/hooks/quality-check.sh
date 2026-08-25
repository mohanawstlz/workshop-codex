#!/bin/bash
# Quality gate: lint the files Codex just changed
for f in $(git diff --name-only); do
  case "$f" in
    *.js|*.jsx|*.ts|*.tsx)
      command -v eslint &> /dev/null && eslint "$f" --quiet
      command -v prettier &> /dev/null && prettier --check "$f"
      ;;
    *.py)
      command -v ruff &> /dev/null && ruff check "$f"
      command -v black &> /dev/null && black --check "$f"
      ;;
    *.go)
      command -v gofmt &> /dev/null && gofmt -l "$f"
      ;;
  esac
done
