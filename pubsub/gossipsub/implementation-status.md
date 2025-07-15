# Implementation status of Gossipsub versions and Extensions

This doc is meant to provide an overview of the implementation status of
Gossipsub versions and Extensions.

## Gossipsub Versions

|               | [1.2] | [1.3-alpha]                                                    |
| ------------- | ----- | -------------------------------------------------------------- |
| [Go libp2p]   | ✅    | [Open PR](https://github.com/libp2p/go-libp2p-pubsub/pull/630) |
| [Rust libp2p] | ✅    | In Progress                                                    |
| [JS libp2p]   | ✅    | Not started                                                    |
| [Nim libp2p]  | ✅    | Not started                                                    |
| [Java libp2p] | ✅    | Not started                                                    |

## Gossipsub Extensions

|               | [Choke Extensions] | [Partial Messages] |
| ------------- | ------------------ | ------------------ |
| [Go libp2p]   | Not Implemented    | PR Soon            |
| [Rust libp2p] | Not Implemented    | Not Implemented    |
| [JS libp2p]   | Not Implemented    | Not Implemented    |
| [Nim libp2p]  | Not Implemented    | Not Implemented    |
| [Java libp2p] | Not Implemented    | Not Implemented    |

## Gossipsub Implementation Improvements

|               | [Batch Publishing]                                                       | [IDONTWANT on First Publish]                              | [WFR Gossip]          |
| ------------- | ------------------------------------------------------------------------ | --------------------------------------------------------- | --------------------- |
| [Go libp2p]   | [✅](https://pkg.go.dev/github.com/libp2p/go-libp2p-pubsub#MessageBatch) | [✅](https://github.com/libp2p/go-libp2p-pubsub/pull/612) | In Progress (PR Soon) |
| [Rust libp2p] | Not Implemented                                                          | [✅](https://github.com/libp2p/rust-libp2p/pull/5773)     | Not Implemented       |
| [JS libp2p]   | Not Implemented                                                          | Not Implemented                                           | Not Implemented       |
| [Nim libp2p]  | Not Implemented                                                          | Not Implemented                                           | Not Implemented       |
| [Java libp2p] | Not Implemented                                                          | Not Implemented                                           | Not Implemented       |

[Go libp2p]: https://github.com/libp2p/go-libp2p-pubsub
[Rust libp2p]: https://github.com/libp2p/rust-libp2p/tree/master/protocols/gossipsub
[JS libp2p]: https://github.com/ChainSafe/js-libp2p-gossipsub
[Nim libp2p]: https://github.com/vacp2p/nim-libp2p/tree/master/libp2p/protocols/pubsub/gossipsub
[Java libp2p]: https://github.com/libp2p/jvm-libp2p/tree/develop/libp2p/src/test/kotlin/io/libp2p/pubsub/gossip
[1.2]: https://github.com/libp2p/specs/blob/master/pubsub/gossipsub/gossipsub-v1.2.md
[1.3-alpha]: https://github.com/libp2p/specs/issues/687
[Choke Extensions]: https://github.com/libp2p/specs/pull/681
[Partial Messages]: https://github.com/libp2p/specs/pull/685
[Batch Publishing]: https://ethresear.ch/t/improving-das-performance-with-gossipsub-batch-publishing/21713
[IDONTWANT on first Publish]: https://github.com/libp2p/go-libp2p-pubsub/issues/610
[WFR Gossip]: https://ethresear.ch/t/the-paths-of-least-resistance-introducing-wfr-gossip/22671/3
