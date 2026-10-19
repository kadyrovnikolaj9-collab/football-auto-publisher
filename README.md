# Football Auto Publisher

A small free-to-run football news publisher for a VK community, scheduled with GitHub Actions.

## What it does
- Reads Russian-language football headlines from Google News RSS.
- Publishes a short headline, source, and link to VK.
- Keeps a small local history to avoid posting the same story repeatedly.
- Runs on a schedule using GitHub Actions.

## Setup
1. Create a VK community and obtain a community access token with permission to publish wall posts.
2. In this GitHub repository, open **Settings → Secrets and variables → Actions** and add:
   - `VK_ACCESS_TOKEN`: the community access token.
   - `VK_GROUP_ID`: the numeric community ID (digits only, without a minus sign).
3. Open **Settings → Actions → General** and allow workflows to read and write repository contents, so the bot can save its duplicate-prevention history.
4. Open **Actions** and enable workflows if GitHub asks.
5. Run **Football news publisher** manually once from Actions to test.

## Safety and content
The bot posts headlines, publisher names, and links, not full articles or other publishers' photos/videos. Verify source terms before expanding the content types. Never commit access tokens to the repository.

## Current limits
This first version uses an RSS feed and posts text only. It does not yet collect match scores, statistics, images, videos, or memes, and it cannot publish until the VK community and secrets are configured.
