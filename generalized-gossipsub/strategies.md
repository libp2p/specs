# Strategies

These are extensible "modules" that give extra degrees of freedom to customizing
the core gossipsub protocol on a per-topic and per-time basis.

They control how meshes are formed (mesh strategy) and how messages are
disseminated through the formed networks (broadcast strategy).

These strategies are defined below

## Mesh Strategies

These strategies define the general topology of a network. They decide how peers
get connected and how the overlay network gets formed. This can give designers a
balance between lean broadcast trees and heavily connected networks by selecting how many and who will form mesh peers.

A host of network-specific strategies can be made to produce a range of varying overlay networks which can be distinct per-topic.

### Interface

This section defines the basic logical interface that defines a mesh strategy. The exact API of how a mesh strategy interfaces with the core
protocol is left to each specific implementation.

#### JOIN(Topic)

When our router joins a topic, a new mesh may need to be formed. This module
will need to define how a new mesh is constructed given the known set of peers subscribed to a topic.

#### SUBSCRIBE(Topic)

A new peer has subscribed to a topic. The mesh strategy may wish to include this
peer into the mesh and inform the router to send a GRAFT (given the current mesh
state).

#### GRAFT(Topic)

A graft message has been received. The mesh strategy needs to decide if the
newly grafted peer aligns with its strategy and whether a PRUNE should be sent
to remove this peer.

#### Heartbeat

The heartbeat is a periodic process that can be used by a mesh strategy to
perform mesh and fanout maintenance. Various mesh strategies may wish to
regularly churn, add or remove peers from the mesh and fanout lists.

## Broadcast Strategies

These strategies define how messages are broadcast through the network. They set
how eagerly we send messages, whether we direct send them or gossip them and how
often. These strategies can effectively provide tradeoffs between latency,
bandwidth and redundancy on a per-topic, per-time basis.

### Interface

This section defines the basic logical interface that defines a mesh strategy. The exact API of how a mesh strategy interfaces with the core
protocol is left to each specific implementation.

#### Publish(Topic) and Forward(Topic)

When a message is published, the core protocol will inform the broadcast
strategy of all connected peers on this topic and the mesh peers of this topic.
The strategy will inform the core protocol of the following

- Which peers to directly publish the message to
- Which peers to gossip (send an IHAVE) the message to (immediately)

#### IHAVE(msg-ids)

This optional interface can opt to not request messages via IWANTs if desired.

#### Heartbeat

The heartbeat is a periodic process that can be used by a broadcast strategy to
emmit gossip or broadcast messages.

## Scoring Strategies

TODO: There is a pretty clean interface for the 1.1 scoring, will update here.
