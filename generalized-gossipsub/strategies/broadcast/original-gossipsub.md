# Original Broadcast Strategy

This module defines the broadcast/routing mechanics of the original gossipsub design.

This router is based on randomized topic meshes and gossip. It is a general purpose pubsub protocol
with moderate amplification factors and good scaling properties.

## Parameters

This section lists the configurable parameters that control the behavior of
gossipsub, along with a short description and reasonable defaults. Each
parameter is introduced with full context elsewhere in this document.

| Parameter | Purpose                                            | Reasonable Default |
| --------- | -------------------------------------------------- | ------------------ |
| `D_lazy`  | (Optional) the outbound degree for gossip emission | `D`                |

Note that `D_lazy` is used to control the outbound
degree when [emitting gossip](#gossip-emission), which may be tuned separately
than the degree for eager message propagation.

## Interface Implementation

### Publish(Topic) and Forward(Topic)

- If the router is subscribed to the topic, it will send the message to all
  peers in `mesh[topic]`.
- If the router is not subscribed to the topic, it will examine the set of peers
  in `fanout[topic]`. If this set is empty, the router will choose up to `D`
  peers from `peers.gossipsub[topic]` and add them to `fanout[topic]`. Assuming
  there are now some peers in `fanout[topic]`, the router will send the message
  to each.

### Forward(Topic)

If the message has not been previously seen, the router will forward the message to every peer in its local topic mesh, contained in `mesh[topic]`.

### Graft(Topic)

All graft links are accepted, no Prune is necessary.

### Heartbeat

Gossip is emitted to a random selection of peers for each topic that are not
already members of the topic mesh:

```
for each topic in mesh+fanout:
  let mids be mcache.get_gossip_ids(topic)
  if mids is not empty:
    select D_lazy peers from peers.gossipsub[topic]
    for each peer not in mesh[topic] or fanout[topic]
      emit IHAVE(mids)

shift the mcache

```
