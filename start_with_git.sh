
#!/bin/bash

# Start Git auto-update in background
./git_auto_update.sh &

# Start the project workflows
python main.py
