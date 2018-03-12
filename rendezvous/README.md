# Rendezvous Service

Scope:
- real-time applications that require rendezvous; replace ws-star-rendezvous
  in conjunction with p2p-circuit relays.

## Rendezvous Protocol

The rendezvous protocol provides facilities for real-time peer discovery within
application specific namespaces. Peers connect to the rendezvous service and register
their presence in one or more namespaces; they can subsequently enter rendezvous
and receive announcements about peer registrations and unregistrations within their
namespaces of interest. Registrations persist until the peer disconnects or explicitly
unregisters.

### Interaction

Client peer `A` connects to the rendezvous service `R` and registers for namespace
`my-app` with a `REGISTER` message. It subsequently enters rendezvous with
a `RENDEZVOUS` message and waits for `REGISTER`/`UNREGISTER` announcements from
the service.

```
A -> R: REGISTER{my-app, {QmA, AddressA}}
A -> R: RENDEZVOUS{my-app}
```

Client peer `B` connects, registers and enters rendezvous.
The rendezvous service immediately notifies `B` about the current namespace registrations
and emits a register notification to `A`:

```
B -> R: REGISTER{my-app, {QmB, AddressB}}
B -> R: RENDEZVOUS{my-app}

R -> B: REGISTER{my-app, {QmA, AddressA}}
R -> A: REGISTER{my-app, {QmB, AddressB}}
```

A third client `C` connections and registers:
```
C -> R: REGISTER{my-app, {QmC, AddressC}}
C -> R: RENDEZVOUS{my-app}

R -> C: REGISTER{my-app, {QmA, AddressA}}
R -> C: REGISTER{my-app, {QmB, AddressB}}
R -> A: REGISTER{my-app, {QmC, AddressC}}
R -> B: REGISTER{my-app, {QmC, AddressC}}
```

### Protobuf


```protobuf
message Message {
  enum MessageType {
    REGISTER = 0;
    UNREGISTER = 1;
    RENDEZVOUS = 2;
  }

  message Peer {
    optional string id = 1;
    repeated bytes addrs = 2;
  }

  message Register {
    optional string ns = 1;
    optional Peer peer = 2;
  }

  message Unregister {
    optional string ns = 1;
    optional Peer peer = 2;
  }

  message Rendezvous {
    optional string ns = 1;
  }

  optional MessageType type = 1;
  repeated Register register = 2;
  repeated Unregister unregister = 3;
  repeated Rendezvous rendezvous = 4;
}
```
