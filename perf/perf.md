# Perf <!-- omit in toc -->

| Lifecycle Stage | Maturity      | Status | Latest Revision |
| --------------- | ------------- | ------ | --------------- |
| 1A              | Working Draft | Active | r0, 2022-11-16  |

Authors: [@marcopolo]

Interest Group: [@marcopolo], [@mxinden], [@marten-seemann]

[@marcopolo]: https://github.com/marcopolo
[@mxinden]: https://github.com/mxinden
[@marten-seemann]: https://github.com/marten-seemann

# Table of Contents <!-- omit in toc -->
- [Context](#context)
- [Protocol](#protocol)
- [Benchmarks](#benchmarks)
  - [Single connection throughput](#single-connection-throughput)
  - [Handshakes per second](#handshakes-per-second)
- [Security Considerations](#security-considerations)
- [Prior Art](#prior-art)

# Context

The `perf` protocol represents a standard benchmarking protocol that we can use
to talk about performance within and across libp2p implementations. This lets us
analyze peformance, guide improvements, and protect against regressions.

# Protocol

The `/perf/1.0.0` protocol (from here on referred to as simply `perf`) is a
client driven set of benchmarks. To not reinvent the wheel, this perf protocol
is almost identical to Nick Bank's [_QUIC Performance_
Internet-Draft](https://datatracker.ietf.org/doc/html/draft-banks-quic-performance#section-2.3)
but adapted to libp2p.
The protocol first performs an upload of a client-chosen amount of bytes. Once
that upload has finished, the server sends back as many bytes as the client
requested.

The bytes themselves should be a predetermined arbitrary set of bytes. Zero is
fine, but so is random bytes (as long as it's not a different set of random
bytes, because then you may be limited by how fast you can generate random
bytes).


The protocol is as a follows:

Client:

1. Open a libp2p stream to the server.
2. Tell the server how many bytes we want the server to send us as a single
   big-endian uint64 number. Zero is a valid number, so is the max uint64 value.
3. Write some amount of data to the stream.
     Zero is a valid amount.
4. Close the write side of our stream.
5. Read from the read side of the stream. This
   should be the same number of bytes as we told the server in step 2.

Server, on handling a new `perf` stream:
1. Read the big-endian uint64 number. This is how many bytes we'll send back in step 3.
2. Read from the stream until we get an `EOF` (client's write side was closed).
3. Send the number of bytes defined in step 1 back to the client. This MUST NOT be run
   concurrently with step 2.
5. Close the stream.

# Benchmarks

The above protocol is flexible enough to run the following benchmarks and more.
The exact specifics of the benchmark (e.g. how much data to download or for how
long) are left up to the benchmark implementation. Consider these rough
guidelines for how to run one of these benchmarks.

Other benchmarks can be run with the same protocol. The following benchmarks
have immediate usefulness, but other benchmarks can be added as we find them
useful. Consult the [_QUIC Performance_
Internet-Draft](https://datatracker.ietf.org/doc/html/draft-banks-quic-performance#section-2.3)
for some other benchmarks (called _scenarios_ in the document).

## Single connection throughput

For an upload test, the client sets the the server response size to 0 bytes, writes
some amount of data and closes the stream.

For a download test, the client sets the server response size to N bytes, and
closes the write side of the data.

The measurements are gathered and reported by the client by measuring how many
bytes were transferred by the total time it took from stream open to stream
close.

A timer based variant is also possible where we see how much data a client can
upload or download within a specific time. For upload it's the same as before
and the client closes the stream after the timer ends. For download, the client
should request a response size of max uint64, then close the stream after the
timer ends.

## Handshakes per second

This benchmark measures connection setup efficiency. A transport that takes many
RTTs will perform worse here than one that takes fewer.

To run this benchmark:
1. Set up N clients
2. Each client opens K connections/s to a single server
3. once a connection is established, the client closes it and establishes
   another one.

handshakes per second are calculated by taking the total number of connections
successfully established and divide it by the time period of the test.

# Security Considerations

Since this protocol lets clients ask servers to do significant work, it
SHOULD NOT be enabled by default in any implementation. Users are advised not to
enable this on publicly reachable nodes.

Authentacting by Peer ID could mitigate the security concern by only allowing
trusted clients to use the protocol. Support for this is left to the implementation.

# Prior Art

As mentioned above, this document is inspired by Nick Bank's: [QUIC Performance Internet-Draft](https://datatracker.ietf.org/doc/html/draft-banks-quic-performance)

[iperf](https://iperf.fr)

[@mxinden's libp2p perf](https://github.com/mxinden/libp2p-perf)

[@marten-seemann's libp2p perf test](https://github.com/marten-seemann/libp2p-perf-test/)

[@vyzo's libp2p perf test](https://github.com/vyzo/libp2p-perf-test/)
