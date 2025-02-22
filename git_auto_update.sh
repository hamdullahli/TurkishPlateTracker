
#!/bin/bash

while true; do
    # Check for changes
    git add .
    git status | grep "Changes to be committed" > /dev/null

    if [ $? -eq 0 ]; then
        echo "Changes detected, committing and pushing..."
        git commit -m "Auto-update: $(date)"
        git push
    else
        echo "No changes detected"
    fi

    # Wait for 5 minutes before next check
    sleep 300
done
