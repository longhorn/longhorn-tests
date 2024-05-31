---
title: Physical node reboot
---
1. Create StatefulSet/Deployment with 3 a replicas volume.
2. Reboot the volume node that the controller (StatefulSet/Deployment) attached to. After the reboot is complete, the volume should be healthy and the data should be correct.
