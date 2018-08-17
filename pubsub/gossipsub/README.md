# gossipsub: An extensible baseline pubsub protocol

Implementation status:
- Go: [libp2p/go-floodsub#67](https://github.com/libp2p/go-floodsub/pull/67) (experimental)
- JS: not yet started
- Rust: not yet started
- Gerbil: [vyzo/gerbil-simsub](https://github.com/vyzo/gerbil-simsub) (very first implementation)

The below specification is extracted verbatim from the [gerbil-simsub specifcation](https://github.com/vyzo/gerbil-simsub/blob/master/README.org). If there are any discrepancies between the source and quotation, the source should be regarded as the authoritative reference.

* A PubSub Protocol and its Simulator

This is a pubsub protocol, dubbed ~gossipsub~, aka ~meshsub/1.0.0~.
The basic idea is to start from a connected network with an arbitrary
degree and reduce it to a mesh with a specific degree. Messages are
forwarded through the reduced mesh. The mesh is augmented by /gossip/
about forwarded messages, which is regularly forwarded to a random subset
of known peers with a heartbeat.

* Reference Implementation

The reference code is written in [[https://github.com/vyzo/gerbil][Gerbil]], and you can install it through the
Gerbil package manager:

#+BEGIN_EXAMPLE
$ gxpkg install github.com/vyzo/gerbil-simsub
#+END_EXAMPLE

* The gossipsub Protocol

The gossipsub router is implemented as an /actor/ in [[simsub/gossip.ss]].

** Protocol
The protocol is defined in two layers: basic pubsub, and gossipsub:

#+BEGIN_SRC gerbil
(defproto pubsub
  event:
  (connect)
  (publish id data))

(defproto gossipsub
  extend: pubsub
  event:
  (ihave ids)
  (iwant ids)
  (graft)
  (prune))
#+END_SRC

The baseline ~pubsub~ protocol specifies 2 messages:
- ~CONNECT~ which establishes a symmetric connection to the peer.
- ~PUBLISH~ which forwards a message to the peer.

The baseline protocol provides just the primitives to connect the
overlay with ~CONNECT~ and forward messages to peers with ~PUBLISH~.
A basic implementation of ~pubsub~, aka ~floodsub~, utilizes flooding:
upon receiving a published message, the peer forwards it to all known
peers except the origin.

The ~gossipsub~ protocol layers on top and augments the baseline protocol with 4
 control messages:
- ~IHAVE~ is the gossip message, which specifies recent messages ids in the peer's
  history.
- ~IWANT~ is used to ask for specific messages by id.
- ~GRAFT~ is used to notify a peer that a mesh link has been grafted.
- ~PRUNE~ is used to notify a peer that a mesh link has been pruned or to reject
  a ~GRAFT~.

In contrast to ~floodsub~, ~gossipsub~ reduces the publish
amplification by routing only through mesh peers. The ~gossipsub~
router maintains the mesh by using ~GRAFT~ and ~PRUNE~ messages, which
effect symmetric links. The mesh is augmented by gossip messages,
~IHAVE~ and ~IWANT~, which allows the overlay to overcome connectivity
pathologies and jump hops opportunistically. More advanced ~gossipsub~
routers can utilize gossip propagation to optimize the overlay for
certain configurations -- e.g. an epidemic broadcast tree router can
~GRAFT~ on fresh gossip and ~PRUNE~ on late messages in order to
optimize for single source transmission.

** Overlay Parameters

#+BEGIN_SRC gerbil
(def N 6)                            ; target mesh degree
(def N-low 4)                        ; low water mark for mesh degree
(def N-high 12)                      ; high water mark for mesh degree

(def history-gossip 3)               ; length of gossip history
(def history-length 120)             ; length of total message history
#+END_SRC

** Actor State

#+BEGIN_SRC gerbil
  (def messages (make-hash-table-eqv))  ; messages seen: message-id -> data
  (def window [])                       ; messages in current window: [message-id ...]
  (def history [])                      ; message history: [window ...]
  (def peers [])                        ; connected peers
  (def D [])                            ; direct peers in the mesh
  (def heartbeat                        ; next heartbeat time
    (make-timeout (1+ (random-real))))
#+END_SRC

** Reaction Loop

The reaction loop implements the main logic loop of the actor. The actor
receives new messages and reacts accordingly, and dispatches the
heartbeat procedure when the timeout is reached.

#+BEGIN_SRC gerbil
  (def (loop)
    (<- ((!pubsub.connect)
         (unless (memq @source peers)
           (set! peers (cons @source peers))))

        ((!pubsub.publish id msg)
         (unless (hash-get messages id) ; seen?
           (hash-put! messages id msg)
           (set! window (cons id window))
           ;; deliver
           (receive id msg)
           ;; and forward
           (for (peer (remq @source D))
             (send! (!!pubsub.publish peer id msg)))))

        ((!gossipsub.ihave ids)
         (let (iwant (filter (lambda (id) (not (hash-get messages id)))
                             ids))
           (unless (null? iwant)
             (send! (!!gossipsub.iwant @source iwant)))))

        ((!gossipsub.iwant ids)
         (for (id ids)
           (alet (msg (hash-get messages id))
             (send! (!!pubsub.publish @source id msg)))))

        ((!gossipsub.graft)
         (unless (memq @source D)
           (set! D (cons @source D))))

        ((!gossipsub.prune)
         (when (memq @source D)
           (set! D (remq @source D))))

        (! heartbeat (heartbeat!)))
    (loop))
#+END_SRC

** Heartbeat

The heartbeat is responsible for actor state management and runs once a second:
- when the mesh degree of the peer is less than the low water mark,
  it selects some random known peers, adds them to the mesh
  peer list, and emits ~GRAFT~ messages to notify them.
- when the mesh degree of the peer is more than the high water mark,
  it selects some random mesh peers, drops them from the mesh
  peer list, and emits ~PRUNE~ messages to notify them.
- the history of messages is rolled by 1, and if it exceeds
  ~history-length~, the earliest seen messages are forgotten.
- The message ids of messages seen in the last ~history-gossip~ windows
  are forwarded to ~N~ random peers with an ~IHAVE~ gossip message.

#+BEGIN_SRC gerbil
  (def (heartbeat!)
    (def d (length D))

    ;; overlay management
    (when (< d N-low)
      ;; we need some links, add some peers and send GRAFT
      (let* ((i-need (- N d))
             (candidates (filter (lambda (peer) (not (memq peer D)))
                                 peers))
             (candidates (shuffle candidates))
             (new-peers (if (> (length candidates) i-need)
                          (take candidates i-need)
                          candidates)))
        (for (peer new-peers)
          (send! (!!gossipsub.graft peer)))
        (set! D (append D new-peers))))

    (when (> d N-high)
      ;; we have too many links, drop some peers and send PRUNE
      (let* ((to-drop (- d N))
             (candidates (shuffle D))
             (pruned-peers (take candidates to-drop)))
        (for (peer pruned-peers)
          (send! (!!gossipsub.prune peer)))
        (set! D (filter (lambda (peer) (not (memq peer pruned-peers)))
                        D))))

    ;; message history management
    (set! history (cons window history))
    (set! window [])
    (when (> (length history) history-length)
      (let (ids (last history))
        (set! history
          (drop-right history 1))
        (for (id ids)
          (hash-remove! messages id))))

    ;; gossip about messages in our history (if any)
    (let (ids (foldl (lambda (window r) (foldl cons r window))
                     []
                     (if (> (length history) history-gossip)
                       (take history history-gossip)
                       history)))
      (unless (null? ids)
        (let* ((peers (shuffle peers))
               (peers (if (> (length peers) N)
                        (take peers N)
                        peers)))
          (for (peer peers)
            (unless (memq peer D)
              (send! (!!gossipsub.ihave peer ids)))))))

    (set! heartbeat (make-timeout 1)))
#+END_SRC

** Initialization

#+BEGIN_SRC gerbil
  (def (connect new-peers)
    (let (new-peers (filter (lambda (peer) (not (memq peer peers)))
                            new-peers))
      (for (peer new-peers)
        (send! (!!pubsub.connect peer)))
      (set! peers
        (foldl cons peers new-peers))))

  (connect initial-peers)
  (loop)
#+END_SRC


* Simulation

The [[simsub/simulator.ss][simulator]] constructs a network of ~N~ nodes, and randomly connects
it with a connectivity degree ~N-connect~.
There is a random latency between any pair of nodes, selected uniformly
in the ~[.01s, .15s]~ interval.
The simulation [[simsub/scripts.ss][script]] sends a number ~M~ of messages, by selecting ~fanout~ random
peers and publishing to them. Each successive message is sent after some delay
~M-delay~.

Here are some example simulations with 100 and 1000 nodes:

#+BEGIN_EXAMPLE
$ gxi
> (import :vyzo/simsub/scripts)
> (simple-gossipsub-simulation trace: void) ; N = 100, N-connect = 10, M = 10, M-delay = 1
=== simulation summary ===
nodes: 100
messages: 10
fanout: 5
publish: 50
deliver: 1000
!!gossipsub.graft: 380
!!pubsub.connect: 1000
!!gossipsub.prune: 7
!!gossipsub.iwant: 31
!!pubsub.publish: 6473
!!gossipsub.ihave: 4402

> (simple-gossipsub-simulation trace: void messages: 100 message-delay: .1)
=== simulation summary ===
nodes: 100
messages: 100
fanout: 5
publish: 500
deliver: 10000
!!gossipsub.graft: 374
!!pubsub.connect: 1000
!!gossipsub.prune: 8
!!gossipsub.iwant: 163
!!pubsub.publish: 63351
!!gossipsub.ihave: 4844

> (simple-gossipsub-simulation trace: void messages: 1000 message-delay: .01)
=== simulation summary ===
nodes: 100
messages: 1000
fanout: 5
publish: 5000
deliver: 100000
!!gossipsub.graft: 376
!!pubsub.connect: 1000
!!gossipsub.iwant: 1037
!!pubsub.publish: 646973
!!gossipsub.ihave: 8413

> (simple-gossipsub-simulation trace: void nodes: 1000)
=== simulation summary ===
nodes: 1000
messages: 10
fanout: 5
publish: 50
deliver: 10000
!!gossipsub.graft: 3651
!!pubsub.connect: 10000
!!gossipsub.prune: 15
!!gossipsub.iwant: 155
!!pubsub.publish: 61957
!!gossipsub.ihave: 45456

> (simple-gossipsub-simulation trace: void nodes: 1000 messages: 100 message-delay: .5)
=== simulation summary ===
nodes: 1000
messages: 100
fanout: 5
publish: 500
deliver: 100000
!!gossipsub.graft: 3661
!!pubsub.connect: 10000
!!gossipsub.prune: 21
!!gossipsub.iwant: 1146
!!pubsub.publish: 621559
!!gossipsub.ihave: 198372

> (simple-gossipsub-simulation trace: void nodes: 1000 messages: 100 message-delay: .1)
=== simulation summary ===
nodes: 1000
messages: 100
fanout: 5
publish: 500
deliver: 100000
!!gossipsub.graft: 3740
!!pubsub.connect: 10000
!!gossipsub.prune: 53
!!gossipsub.iwant: 20749
!!pubsub.publish: 653634
!!gossipsub.ihave: 84297

#+END_EXAMPLE

Note that as you run bigger simulations, you'll need a faster computer or
the simulator will lag. This can still be useful, as it analyzes the behaviour
of the protocol in extreme lag conditions, where messages can take seconds to
propagate some links.

If you want to see a trace of the developing simulation,
then omit the ~trace: void~ argument to the simulation invocation.
The default ~trace:~ will be ~displayln~, which will print out the simulation
in the current output port.

The simulator also accepts a transcript procedure, which can save the simulation
trace to a file when it ends. For example, the following transcript function will
save the trace to ~/tmp/simsub.out~:

#+BEGIN_EXAMPLE
(def (transcript trace)
  (let (trace (reverse trace))
    (call-with-output-file "/tmp/simsub.out"
      (lambda (port)
        (parameterize ((current-output-port port))
          (for-each displayln trace))))))

> (simple-gossipsub-simulation trace: void transcript: transcript)
...
#+END_EXAMPLE

* License

MIT; © 2018 vyzo

