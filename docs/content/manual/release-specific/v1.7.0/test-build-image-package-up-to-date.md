---
title: System Packages Are Up-to-date During Image Build
---

## Related issues

- https://github.com/longhorn/longhorn/issues/8721

## Test step

**Given** Build Longhorn component images manually.
- longhorn-cli
- longhorn-engine
- longhorn-instance-manager
- longhorn-share-manager
- longhorn-ui

**When** Run a shell within Longhorn component images using Docker.
```bash
docker run --entrypoint bash --user root -it <IMAGE>
```
**And** Execute `zypper ref && zypper update` command inside the container.

**Then** Verify that the command outputs `Nothing to do`.
```shell
> zypper ref && zypper update
Refreshing service 'container-suseconnect-zypp'.
Retrieving repository 'SLE_BCI' metadata ...............................................................................................................[done]
Building repository 'SLE_BCI' cache ....................................................................................................................[done]
Warning: The gpg key signing file 'repomd.xml' has expired.
  Repository:       snappy
  Key Fingerprint:  4F2F A05B 2C65 89C3 FD12 055E F7C6 E425 ED34 0235
  Key Name:         system:snappy OBS Project <system:snappy@build.opensuse.org>
  Key Algorithm:    RSA 2048
  Key Created:      Sat Oct 31 16:59:39 2020
  Key Expires:      Mon Jan  9 16:59:39 2023 (EXPIRED)
  Rpm Name:         gpg-pubkey-ed340235-5f9d97fb
Retrieving repository 'snappy' metadata ................................................................................................................[done]
Building repository 'snappy' cache .....................................................................................................................[done]
All repositories have been refreshed.
Refreshing service 'container-suseconnect-zypp'.
Loading repository data...
Reading installed packages...
Nothing to do.
```
