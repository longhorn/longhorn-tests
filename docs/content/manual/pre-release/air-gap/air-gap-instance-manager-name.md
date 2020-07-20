---
title: Air gap installation with an instance-manager-image name longer than 63 characters
---
1. Host instance manager image under a name more than 63 characters in Docker hub
2. Update longhorn-manager deployment flag --instance-manager-image to that value
3. Try to create a new volume and attach it.

Expected behavior:There should be no error.
