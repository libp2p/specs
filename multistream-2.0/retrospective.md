# Multistream-Select 1.0.0 Retrospective

This short document aims to motivate the need for a new stream negotiation
protocol.

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
