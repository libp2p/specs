# Ping <!-- omit in toc -->

| Lifecycle Stage | Maturity                 | Status | Latest Revision |
| --------------- | ------------------------ | ------ | --------------- |
| 1A              | Candidate Recommendation | Active | r0, 2022-11-04  |

Authors: [@marcopolo]

Interest Group: [@marcopolo], [@mxinden], [@marten-seemann]

[@marcopolo]: https://github.com/mxinden
[@mxinden]: https://github.com/mxinden
[@marten-seemann]: https://github.com/marten-seemann

# Table of Contents <!-- omit in toc -->
- [Protocol](#protocol)
- [Diagram](#diagram)

# Protocol

The ping protocol is a simple request response protocol. The client sends a
payload of 32 random bytes, and the server responds with the same 32 bytes. The
client then measures the RTT from the time it wrote the bytes to the time it
received the bytes. The client may repeat the process by sending another payload
with random bytes, so the server _should_ loop and echo the next payload. The
client may close the write side of the stream after sending a payload, the
server _should_ finish writing the echoed payload and then exit the loop and
close the stream.

The protocol id is `/ipfs/ping/1.0.0`.

# Diagram

![Ping Protocol Diagram](./ping.svg)

<details>
  <summary>Instructions to reproduce diagram</summary>

From the root, run:  `plantuml -tsvg ping/ping.md`

```
@startuml
skinparam backgroundColor white

entity Client
entity Server

== /ipfs/ping/1.0.0 ==
loop until Client closes write
    Client -> Server: 32 random bytes
    Client <- Server: Same 32 random bytes
end
@enduml
```

</details>