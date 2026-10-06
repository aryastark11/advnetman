#!/bin/bash
# Recreates and attaches to the 4-Host Continuous Ping TMUX Session for CSCI 5840 Challenge

SESSION_NAME="pings"

# Check if session exists; if not, create it
tmux has-session -t $SESSION_NAME 2>/dev/null

if [ $? != 0 ]; then
  echo "Creating new tmux session: $SESSION_NAME (4-pane grid)..."
  tmux new-session -d -s $SESSION_NAME -n 'host_pings'
  
  # Split into 2x2 grid
  tmux split-window -h -t $SESSION_NAME:0
  tmux split-window -v -t $SESSION_NAME:0.0
  tmux split-window -v -t $SESSION_NAME:0.2
  
  # Enable mouse support for easy scrolling & clicking
  tmux set -g mouse on -t $SESSION_NAME
  
  # Set large history scrollback (10,000 lines)
  tmux set -g history-limit 10000 -t $SESSION_NAME
  
  # Launch continuous pings
  tmux send-keys -t $SESSION_NAME:0.0 "clear && echo '=== HOST H1 (IPv4 -> Web Server) ===' && docker exec -it clab-lab1-h1 ping -O -D -i 1 198.51.100.10" C-m
  tmux send-keys -t $SESSION_NAME:0.1 "clear && echo '=== HOST H3 (IPv4 -> Web Server) ===' && docker exec -it clab-lab1-h3 ping -O -D -i 1 198.51.100.10" C-m
  tmux send-keys -t $SESSION_NAME:0.2 "clear && echo '=== HOST H2 (IPv4 -> Web Server) ===' && docker exec -it clab-lab1-h2 ping -O -D -i 1 198.51.100.10" C-m
  tmux send-keys -t $SESSION_NAME:0.3 "clear && echo '=== HOST H4 (IPv6-Only -> Web Server) ===' && docker exec -it clab-lab1-h4 ping -6 -O -D -i 1 2001:db8:100::10" C-m
fi

echo "Attaching to tmux session '$SESSION_NAME'..."
tmux attach-session -t $SESSION_NAME
