## CXH FP Telegram profile

This folder controls the bot photo and profile text. Changes apply automatically at the next bot start.

The profile name is CXH FP. The fox is the bot mascot; Russian and English descriptions start with 🦊 CXH FP. The project channel is @funpay_coxerhub, the community chat is @coxerhub_ch, and the developer contact is @coxerhub.

| File | Purpose |
| --- | --- |
| avatar.jpg | Telegram avatar, square JPEG |
| description.txt | Full Russian description, up to 512 characters |
| short-description.txt | Russian profile bio, up to 120 characters |
| description.en.txt | Full English description |
| short-description.en.txt | English profile bio |

Save text files as UTF-8. Keep the channel @funpay_coxerhub and contact @coxerhub accurate. Choose a square JPEG for the photo. The bot applies these files to the bot associated with the configured Telegram token. Unchanged photos are not uploaded again.

Missing text files use the built-in description. Invalid text is rejected before any profile text is changed, and the store continues running. The folder is part of the project; the data backup archive covers configs, plugins and storage, so keep a separate copy of any custom profile assets.
