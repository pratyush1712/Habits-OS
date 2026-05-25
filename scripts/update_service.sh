#!/bin/zsh
set -euo pipefail

cd /Users/praty/Code/Habits-OS

git pull
make setup

./scripts/restart_service.sh