# gossipsub v2.0: Lower or zero duplicates by lazy mesh propagation

| Lifecycle Stage | Maturity       | Status | Latest Revision |
|-----------------|----------------|--------|-----------------|
| 1A              | Working Draft  | Active | r0, 2024-12-13  |

Authors: [@ppopth], [@nisdas], [@chirag-parmar]

[@ppopth]: https://github.com/ppopth
[@nisdas]: https://github.com/nisdas
[@chirag-parmar]: https://github.com/chirag-parmar

See the [lifecycle document][lifecycle-spec] for context about the maturity level and spec status.

[lifecycle-spec]: https://github.com/libp2p/specs/blob/master/00-framework-01-spec-lifecycle.md

---

## Overview

This document specifies extensions to [gossipsub v1.2](gossipsub-v1.2.md) intended to allow lazy propagation to mesh peers to reduce the number of duplicates (which can reach zero) in the network trading off with more latency.

<!-- START doctoc generated TOC please keep comment here to allow auto update -->
<!-- DON'T EDIT THIS SECTION, INSTEAD RE-RUN doctoc TO UPDATE -->

- [Background](#background)
  - [Problem With Previous Versions](#problem-with-previous-versions)
- [Enter Gossipsub v2.0](#enter-gossipsub-v20)
- [Protocol extensions](#protocol-extensions)
  - [Parameters](#parameters)
  - [Router State](#router-state)
  - [Control Messages](#control-messages)
    - [IANNOUNCE](#iannounce)
    - [INEED](#ineed)
  - [Message Processing](#message-processing)
  - [Protobuf](#protobuf)
- [Future Improvements](#future-improvements)

<!-- END doctoc generated TOC please keep comment here to allow auto update -->

## Background

Before diving into the motivations for gossipsub v2.0, we can look at gossipsub as of v1.2 to understand how it works.

Gossipsub is a pubsub protocol over lib2p which is based on randomized topic meshes. The general message propagation strategy is to broadcast any message to a subset of its peers. This subset is referred to as the 'mesh'. By controlling the outbound degree of each peer you are also able to control the amplification factor in the network.

By selecting a high enough degree you can achieve a robust network with minimum latency. This allows messages to be dispersed resiliently across a network in a short amount of time.

The mesh that is selected is random and is constantly maintained via gossip control messages to ensure that the quality of peers stays consistent and doesn't deteriorate. Gossip Metadata is emitted during every heartbeat to allow peers who might have missed certain messages due to downstream message loss to be able to recover and retrieve them.

Each peer has a memory of all seen messages in the network over a period of time. This allows nodes to drop duplicates and prevents them from being further disseminated. Also having memory of messages which were propagated allows peers to make scoring decisions on their mesh peers. This allows them to prune lousy peers from the mesh and graft new ones in.

### Problem With Previous Versions

As demonstrated above gossipsub has some very desirable characteristics as a pubsub protocol. However, while you have a resilient network with minimal latency (assuming a high enough degree), Gossipsub as of its current design brings about a high level of amplification.

The tradeoff of the current design is if a network requires messages to be propagated with minimal latency it requires a large amount of amplification. This is problematic in networks which need to propagate large messages, as the amplification done is significant. If many of these large messages start being propagated in a network it would affect the general decentralization and scalability of the network.

For networks such as those Gossipsub v1.2 introduced a new control message called `IDONTWANT`. This control message allows a peer to tell its mesh peers not to propagate a message matching a particular message ID. The main goal of this is to prevent duplicates from being sent and reduce amplification in the network as a whole.

While this does help in reducing duplicates it ultimately relies on remote peers being able to act on the control message in time. If they do not, the message still ends up being forwarded wasting bandwidth on both the sender and the receiver. So how can we improve on this?

## Enter Gossipsub v2.0

Gossipsub v2.0 is an extension to gossipsub v1.2 which reduces the number of duplicates lower or to zero trading off with more latency.

In this extension, instead of sending the messages right away to mesh peers, you send `IANNOUNCE` to them instead and see if they are interested in the message or not. If they are, they can send `INEED`.

After sending `INEED` to mesh peers, if there is no response after some timeout, you send `INEED` to another peer that sent you `IANNOUNCE` earliest. If you still get no response, keep going on.

By doing this, you are guaranteed that you will receive only one copy of messages. However you may need to send the message more than once to your mesh peers which is bound by the degree. Unless you are the publisher or very close to the publisher, you are expected to send only one copy anyway.

The benefits of doing this are numerous, a few of having zero duplicates are listed below:
- In congested networks which have peers with lower bandwidth, reducing the number of duplicates to zero actually improves latency as only one copy of the message passes through each peer.
- The mesh degree can be increased greatly without affecting decentralization. The main reason the degree is bounded was to make sure that bandwidth requirements are maintainable. Since we now have zero duplicates via each link, you can have a message propagated with even less latency (fewer hops are required with a higher degree).

## Protocol extensions

### Parameters

The extensions that make up gossipsub v2.0 introduce several new application configurable parameters. This section summarizes all the new parameters along with a brief description.

The following parameters apply globally:

| Parameter    | Purpose                                                                                    | Reasonable Default |
|--------------|--------------------------------------------------------------------------------------------|--------------------|
| `timeout`    | Timeout for `INEED` messages                                                               | 400 milliseconds   |
| `D_announce` | Desired number of times a message is sent lazily to the mesh. Must be at most equal to `D` | 4                  |


### Router State

We keep an announce cache (or `acache`), which is a collection of queues indexed by messaged IDs. Items in the queues are peer IDs of mesh peers ordered by who sent `IANNOUNCE` with such message id earliest. The purpose of these queues is to know who to send `INEED` first.

### Control Messages

This extension has two new control messages: `IANNOUNCE` and `INEED`.

For details on how gossipsub routers respond to the new control messages, see [Message Processing](#message-processing).

#### IANNOUNCE

The `IANNOUNCE` message is sometimes sent to mesh peers, when the local router receives a new message. It provides the remote peer with a single message id of the message that was recently seen by the local router.

#### INEED

The `INEED` message requests the full content of a single message whose id was announced by a remote peer in an `IANNOUNCE` message.

### Message Processing

Upon receiving a message, the router will first process and validate the message payload as usual.

If the message is valid and has not been previously seen, firstly it clears `acache[msgid]` to prevent sending any more `IANNOUNCE`.

Secondly, for each mesh peer to which the router wants to forward the message, it will toss a coin to decide whether to forward the message eagerly or lazily. The probability of forwarding lazily is determined by `D_announce/D`.

- If the router decides to forward the message eagerly, it will just forward the full message to that mesh peer.
- If the router decides to forward the message lazily, it will send `IANNOUNCE` with the message id attached instead to tell them that it just receives a new message. If they want the full content of the message, they should send `INEED` back.

After processing the message payload, the router will process the new control messages as follows:

- Upon receiving `IANNOUNCE`, the router checks the [`seen` cache][seen-cache] to see if it has been seen or not. If not, it adds the sending peer to `acache[msgid]`, where `msgid` is the one attached to `IANNOUNCE`. If `acache[msgid]` was previously empty, the router pops `acache[msgid]` and sends `INEED` to that peer immediately.

  After the router sends `INEED`, it will time out if it doesn't receive the message back in time, as indicated by `timeout`. If the timeout happens, the router will pop `acache[msgid]` send `INEED` to the next peer. If it still times out, keep going with next peers until the cache runs out of peers.

  Notice that timeouts can delay receiving the message. It's worth noting that timeouts are rare, since the peer just sent the router `IANNOUNCE` so it means the network condition is already good and the peer should be able to send the actual message without problems.

  In gossipsub v2.1, we plan to penalize peers that don't send the message in time.

- Upon receiving `INEED` after sending `IANNOUNCE`, the router must send the full content back without an option to decline. Otherwise it will be deemed misbehaving.

Apart from forwarding received messages, the router can of course publish messages on its own behalf. This is very similar to forwarding received messages. It also has to toss a coin to decide whether to send the message eagerly or lazily.

[seen-cache]: ../gossipsub/gossipsub-v1.0.md#message-cache

### Message Publishing

For message publishing, as long as `D_announce` is less than `D`, full messages are published to our mesh peers. There is no advantage to lazy mesh
propagation as none of the peers have seen the message before. In the event `D_announce` is equivalent to `D` we disable publishing the full message as 
the message originator is trivially identifiable if message propagation is completely announcement based. 

### Protobuf

The protobuf messages are identical to those specified in the [gossipsub v1.2.0 specification](https://github.com/libp2p/specs/blob/master/pubsub/gossipsub/gossipsub-v1.2.md) with the following control message modifications:

```protobuf
message RPC {
    // ... see definition in the gossipsub specification
}

message ControlMessage {
    // messages from v1.2
    repeated ControlIAnnounce iannounce = 6;
    repeated ControlINeed ineed = 7;
}

message ControlIAnnounce {
    optional string topicID = 1;
    optional bytes messageID = 2;
}

message ControlINeed {
    optional bytes messageID = 2;
}
```

## Future Improvements

- Penalize peers that don't send the message in time, after sending `INEED`.
- Let publishers just send the full content of messages to mesh peers, rather than `IANNOUNCE`, because no one has really seen the message before. This saves one RTT, but it will kill anonymity so we are not sure yet to do it.
