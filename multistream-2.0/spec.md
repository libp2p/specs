# Efficient and Sound Protocol Negotiation

This proposal lays out issues that we've encountered with multistream-select and
proposes a replacement protocol. It also lays out an upgrade path from
multistream-select to the new protocol.

## Retrospective

There are 5 concrete issues with multistream select.

multistream-select:

1. requires at least one round trip to be sound.
2. negotiates protocols in series instead of in parallel. 
3. doesn't provide any way to determine which side (possibly both) initiated the
   connection/negotiation.
4. is bandwidth inefficient.
5. punishes long, descriptive, protocol names. 

We ignore 1 and just accept that the protocol has some soundness issues as
actually *waiting* for a response for a protocol negotiation we know will almost
certainly succeed would kill performance.

As for 2, we make sure to remember protocols known to be spoken by the remote
endpoint so we can try to negotiate a known-good protocol first. However, this
is still inefficient.

Issue 3 gets us in trouble with TCP simultaneous connect. Basically, we need a
protocol where both sides can propose a set of protocols to speak and then
deterministically select the *same* protocol. Ideally, we'd also *expose* the
fact that both sides are initiating to the user.

By 4, I mean that we repeatedly send long strings (the protocol names) back and
forth. While long strings *are* more user friendly than, e.g., port numbers,
they're, well, long. This can introduce bandwidth overheads over 30%.

Issue 5 is a corollary of issue 4. Because we send these protocol names *every*
time we negotiate, we don't, e.g., send longer, better protocol names like:

* /ai/protocol/p2p/bitswap/1.0
* /ipfs/QmId.../bitswap/1.0

However, multistream-select was *explicitly designed* with this use-case in
mind.

## Protocols

This document proposes 5 new, micro-protocols with two guiding principles:

1. Composition over complexity.
2. Every byte and round-trip counts.

The protocols are:

1. `multistream/use`: declares the protocol being used using a multicodec.
2. `multistream/dynamic`: declares the protocol being used using a string.
3. `multistream/contextual`: declares the protocol being used using an ephemeral
   protocol ID defined by the *receiver* for the duration of some session (e.g.,
   an underlying connection).
4. `multistream/choose`: allows an initiator to optimistically initiate multiple
   streams, discarding all but one.
5. `multistream/hello`: inform the remote end about (a) which protocols we speak
   and (b) which services we are running. This should replace both identify and
   our current "try every protocol" service discovery system.
   
This document also proposes an auxiliary protocols that we'll need to complete
the picture.

1. `serial-multiplex`: a simple stream "multiplexer" that can multiplex multiple
   streams *in serial* over the same connection. That is, it allows us to return
   to the stream to multistream once we're done with it. This allows us to *try*
   a protocol, fail, and fallback on a slow protocol negotiation.
   
All peers *must* implement `multistream/use` and *should* implement
`serial-multiplex`. This combination will allow us to apply a series of quick
connection upgrades (e.g., to multistream 3.0) with no round trips and no funny
business (learn from past mistakes).

These protocols were *also* designed to eventually support:

1. Hardware. While we *do* use varints, we avoid using them for lengths in the
   fast-path protocols (the non-negotiating ones).
2. Packet protocols. All protocols described here are actually unidirectional
   (at the protocol level, at least) and can work over packet protocols (where
   the end of the packet is an "EOF").

Notes:

1. The "ls" feature of multistream has been removed. While useful, this really
   should be a *protocol*. Given the `serial-multiplex` protocol, this shouldn't be
   an issue.
2. To reduce RTTs, all protocols are unidirectional. Even the negotiation
   protocol, `multistream/choose` (see below for details).

### Multistream Use

The multistream/use protocol is simply two varint multicodecs: the
multistream-use multicodec followed by the multicodec for the protocol to be
used. This protocol is *unidirectional*. If the stream is bidirectional, the
receiver will, by convention, respond the same way.

Every stream starts with multistream-use. Every other protocol defined here will
be assigned a multicodec and selected with multistream/use.

This protocol should *also* be trivial to optimize in hardware simply by prefix
matching (i.e., matching on the first N (usually 16-32) bits of the
stream/message).

* [ ] Q: Technically, the first multicodec is redundant. However, it acts as a
      magic byte that allows us to figure out what's going on. Should we keep
      it? We could just start all streams with a single multicodec representing
      the protocol
* [ ] Q: Should we somehow distinguish between initiator and receiver? Should we
      distinguish between bidirectional and unidirectional? We could even bit
      pack these options into a single byte and use this instead of the leading
      multicodec... Note: distinguishing between bidirectional and
      unidirectional may actually be necessary to be able to eagerly send a
      unidirectional `multistream/hello` message.

### Multistream Dynamic

The multistream/dynamic protocol is like the multistream/use protocol *except*
that it uses a string to identify the protocol. To do so, the initiator simply
sends a fixed-size 16bit length followed by the name of the protocol.

Including the multistream/use portion, the initiator would send:

```
<multistream/use><multistream/dynamic><length(16 bits)><name(string)>
```

Design Note: We *could* use a varint and save a byte in many cases however:

1. We'd either need to buffer the connection or read the varint byte-by-byte.
   Neither of those are really optimal.
2. The length of the name will be dwarf this extra byte.
3. If anyone needs a 64byte name, they're using the *wrong protocol*. Really,
   a single byte length should be sufficient for all reasonable protocol names
   but we're being stupidly conservative here.

### Multistream Contextual

The multistream/contextual protocol is used to select a protocol using a
*receiver specified*, session-ephemeral protocol ID. These IDs are analogues of
ephemeral ports.

In this protocol, the stream initiator sends a 16 bit ID specified by the
*receiver* to the receiver. This is a *unidirectional* protocol.

Format:

```
<multistream/use><multistream/contextual><id(16 bits)>
```

The ID 0 is reserved for saying "same protocol" on a bidirectional stream. The
receiver of a bidirectional stream can't reuse the same contextual ID that the
initiator used as this contextual ID is relative *to* the receiver. Really, this
last rule *primarily* exists to side-step the TCP simultaneous connect issue.

This protocol has *also* been designed to be hardware friendly:

1. Hardware can compare the first 16 bits of the message against
   `<multistream/use><multistream/contextual>`.
2. It can then route the message based on the contextual ID. The fact that these
   IDs are chosen by the *receiver* means that the receiver can reuse the same
   IDs for all connected peers (reusing the same hardware routing table).
   
* [ ] TODO: Just use a varint? Hardware can still do prefix matching and/or only
support IDs that are at most two bytes long.

### Multistream Choose

**WARNING:** this may be too complex/magical. However, it has some really nice
properties. We could also go with a more standard I send you a list of protocols
and you pick one approach but I'd like to consider this one.

The multistream/choose protocol allows an initiator to start multiple streams in
parallel while telling the receiver to only *act* on one of them. This:

1. Allows us to "negotiate" each stream using the other multistream protocols.
   That is, each message/sub-stream recursively uses multistream.
2. Pack data into the initial packet to shave off a RTT in many cases.
3. Support packet transports out of the box.

Each message in this protocol consists of:

```
<stream number (varint)>
<data length (varint)>
```

The initiator can transition to a single one of these streams by sending:

```
<stream number>
0
```

This effectively aborts all the other streams, allowing the chosen stream to
completely take over the channel.

To actually *select* a protocol on a bidirectional channel, the receiver simply
uses one of the other multistream protocols to pick a protocol.

Note: A *simple* implementation of this protocol would simply send a sequence of
protocols as `<stream number 1><length><multistream/use>...<stream number
2><length><multistream/use>...` and then wait for the other side to select the
appropriate protocol.


* [ ] Q: The current framing system is dead simple but inefficient in some
      cases. Specifically, one can't just (a) read a *single* header and then
      (b) jump to the desired sub-stream. Alternatives include:
    * Have a single header that maps stream numbers to offsets and lengths. This
      way, one could jump to the correct section immediately.
    * Have a single list of "sections", no stream numbers. Stream numbers would be
      inferred by index. This is slightly smaller but not very flexible.
* [ ] Q: Avoid varints?
* [ ] Q: Just do something simpler?

### Multistream Hello

Unspeced (for now). Really, we just need to send a mapping of protocol
names/codecs to contextual IDs (and may be some service discovery information).
Basically, identify.

### Serial Multiplex

The `serial-multiplex` protocol is the simplest possible stream multiplexer.
Unlike other stream multiplexers, `serial-multiplex` can only multiplex streams
in *serial*. That is, it has to close the current stream to open a new one. Also
unlike most multiplexers, this multiplexer is *unidirectional*.

The protocol is:

```
<header (signed 16 bit int)>
<body>
```

Where the header is:

* -2 - Send a reset and return to multistream. All queued data (remote and
* -1 - Close: Send an EOF and return to multistream.
*  0 - Rest: Ends the reuse protocol, transitioning to a direct stream.
  local) should be discarded.
* >0 - Data: The header indicates the length of the data.

We could also use a varint but it's not really worth it. The 16 bit integer
makes implementing this protocol trivial, even in hardware.

Why: This allows us to:

1. Try protocols and fall back on others (we can also use `multistream/choose`
   for this).
2. More importantly, it allows us to speak a bunch of protocols before setting
   up a stream multiplexer. Specifically, we can use this for
   `multistream/hello` to send a hello as early as possible.

## Upgrade Path

#### Short term

The short-term plan is to first negotiate multistream 1.0 and *then* negotiate
an upgrade. That is, on connect, the *initiator* will send:

```
<len>/multistream/1.0.0\n
<len>/multistream/2.0.0\n
```

As a batch. It will then wait for the other side to respond with either:

```
<len>/multistream/1.0.0\n
<len>na\n
```

in which case it'll continue using multistream 1.0, or:

```
<len>/multistream/1.0.0\n
<len>/multistream/2.0.0\n
```

in which case it'll switch to multistream 2.0.

Importantly: When we switch to multistream 2.0, we'll tag the connection (and
any sub connections) with the multistream version. This way, we never have to do
this again.
