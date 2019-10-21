# RFC 0002 - Signed Envelopes

- Start Date: 2019-10-21
- Related RFC: [0003 Address Records][addr-records-rfc]

## Abstract

This RFC proposes a "signed envelope" structure that contains an arbitray byte
string payload, a signature of the payload, and the public key that can be used
to verify the signature.

This was spun out of an earlier draft of the [address records
RFC][addr-records-rfc], since it's generically useful.

## Problem Statement

Sometimes we'd like to store some data in a public location (e.g. a DHT, etc),
or make use of potentially untrustworthy intermediaries to relay information. It
would be nice to have an all-purpose data container that includes a signature of
the data, so we can verify that the data came from a specific peer and that it hasn't
been tampered with.

## Wire Format

Since we already have a [protobuf definition for public keys][peer-id-spec], we
can use protobuf for this as well and easily embed the key in the envelope:


```protobuf
message SignedEnvelope {
  PublicKey publicKey = 1; // see peer id spec for definition
  string purpose = 2;      // arbitrary user-defined string for context
  bytes cid = 3;           // CIDv1 of contents
  bytes contents = 4;      // payload
  bytes signature = 5;     // signature of purpose + cid + contents
}
```

The `publicKey` field contains the public key whose secret counterpart was used
to sign the message. This MUST be consistent with the peer id of the signing
peer, as the recipient will derive the peer id of the signer from this key.

The `purpose` field is an aribitrary string that can be used to give some hint
as to the contents. For example, if `contents` contains a serialized
`AddressState` record, `purpose` might contain the string `"AddressState"`. The
contents of the ``purpose`` field are signed alongside `contents` to prevent
tampering, and may be empty if desired.

The `cid` field contains a version 1 [CID][cid] (content id) that corresponds to
the `content` field. It's used for retrieving messages from [local
storage](#local-storage-of-signed-envelopes), and the embedded multicodec also
gives a hint as to the data type of the `contents`. If the user does not specify
a multicodec when constructing the envelope, the default will be
[`raw`](https://github.com/multiformats/multicodec/blob/master/table.csv#L34)
for raw binary.

## Signature Production / Verification

When signing, a peer will prepare a buffer by concatenating the following:

- The string `"libp2p-signed-envelope:"`, encoded as UTF-8
- The `purpose` field, encoded as UTF-8
- The `cid` field
- The `contents` field

Then they will sign the buffer according to the rules in the [peer id
spec][peer-id-spec] and set the `signature` field accordingly.

To verify, a peer will "inflate" the `publicKey` into a domain object that can
verify signatures, prepare a buffer as above and verify the `signature` field
against it.

## Local Storage of Signed Envelopes

Signed envelopes can be used for ephemeral data, but we may also want to persist
them for a while and / or make previously recieved envelopes accesible to
various libp2p modules.

For example, if the envelope contains an [address record][addr-records-rfc],
those records might be used to populate a peer store with self-certified
records. Rather than requiring the peer store to persist the full envelope, we
could have a separate "envelope storage" service that keeps signed messages
around for future reference. 

The peer store can then just store the `cid` alongside a flag that indicates
that the address came from a trusted source. If we're using a persistent peer
store and the process restarts, we can look up the stored `cid` in the envelope
storage and verify the signature again.

If we decide to build this, the storage service should have some kind of garbage
collection / TTL scheme to avoid unbounded growth.

[addr-records-rfc]: ./0003-address-records.md
[peer-id-spec]: ../peer-ids/peer-ids.md
