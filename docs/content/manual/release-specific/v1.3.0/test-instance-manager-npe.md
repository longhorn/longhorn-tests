---
title: Test instance manager NPE 
---

### Test step
1. Create and attach a 1-replica volume.
2. Create 2 snapshots with large amount of data so that rebuilding each snapshot would take some time.
3. Disable the scheduling for the nodes so that there is one node could accept new replicas of the volume.
4. Update the replica count to 2 for the volume and wait for the rebuilding start.
5. While syncing the 1st snapshot file, create a directory with the name of **another snapshot meta file**. 
   Later the rebuilding replica will fail to create this meta file then error out.
6. Verify there is no NPE issue (no following log) in the instance manager pod when the failure mentioned above is triggered.
    ```log
    2021/12/24 16:29:02 http: panic serving 10.42.2.251:42464: runtime error: invalid memory address or nil pointer dereference
    goroutine 88514 [running]:
    net/http.(*conn).serve.func1(0xc00032e000)
        /usr/local/go/src/net/http/server.go:1772 +0x139
    panic(0xd73a40, 0x168d100)
        /usr/local/go/src/runtime/panic.go:975 +0x3e3
    github.com/longhorn/sparse-tools/sparse/rest.(*SyncServer).close(0xc00041c050, 0x108cf60, 0xc00015c000, 0xc000364200)
        /go/src/github.com/longhorn/longhorn-engine/vendor/github.com/longhorn/sparse-tools/sparse/rest/handlers.go:119 +0x63
    net/http.HandlerFunc.ServeHTTP(0xc0001f6830, 0x108cf60, 0xc00015c000, 0xc000364200)
        /usr/local/go/src/net/http/server.go:2012 +0x44
    github.com/gorilla/mux.(*Router).ServeHTTP(0xc0004f6000, 0x108cf60, 0xc00015c000, 0xc00020a300)
        /go/src/github.com/longhorn/longhorn-engine/vendor/github.com/gorilla/mux/mux.go:212 +0xe2
    net/http.serverHandler.ServeHTTP(0xc000428000, 0x108cf60, 0xc00015c000, 0xc00020a300)
        /usr/local/go/src/net/http/server.go:2807 +0xa3
    net/http.(*conn).serve(0xc00032e000, 0x10915a0, 0xc0003ae240)
        /usr/local/go/src/net/http/server.go:1895 +0x86c
    created by net/http.(*Server).Serve
        /usr/local/go/src/net/http/server.go:2933 +0x35c
    ```
7. Verify the rebuilding will be restarted and succeed.
8. Verify the data of the volume.

---
GitHub Issue: https://github.com/longhorn/longhorn/issues/2820