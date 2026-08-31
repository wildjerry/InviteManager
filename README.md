```

# Using Docker Compose

This is the recommended method. 
```yaml
services:
  invitemanager:
    image: ghcr.io/wildjerry/invitemanager:latest
    restart: unless-stopped
    environment:
      DISCORD_TOKEN: ${DISCORD_TOKEN}
      LOG_CHANNEL_ID: ${LOG_CHANNEL_ID}
      TRUSTED_ROLE_ID: ${TRUSTED_ROLE_ID}
      MAX_USES: ${MAX_USES:-5}
      MAX_EXPIRY: ${MAX_EXPIRY:-604800}
```
# Bot

You need the Members intent enabled. I recommend disabling User Application and setting to non public. Your OAUTH link should look like `https://discord.com/oauth2/authorize?client_id=1543820074111082586&permissions=3104&integration_type=0&scope=bot`

# Testing on Linux

Using a venv reccomended.

```

# Source - https://stackoverflow.com/a/43267603
# Posted by Charles Duffy, modified by community. See post 'Timeline' for change history
# Retrieved 2026-08-30, License - CC BY-SA 4.0

set -a # automatically export all variables
source .env
set +a
