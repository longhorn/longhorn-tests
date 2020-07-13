---
title: "[#1341](https://github.com/longhorn/longhorn/issues/1341) concurrent backup test"
---
- Take a manual backup of the volume `bak` while a recurring backup is running
- verify that backup got created 
- verify that backup sticks around even when recurring backups are cleaned up
