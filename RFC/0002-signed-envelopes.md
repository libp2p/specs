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

## Domain Separation

Signatures can be used for a variety of purposes, and a signature made for a
specific purpose MUST NOT be considered valid for a different purpose.

Without this property, an attacker could convince a peer to sign a paylod in one
context and present it as valid in another, for example, presenting a signed
address record as a pubsub message.

We separate signatures into "domains" by prefixing the data to be signed with a
string unique to each domain. This string is not contained within the payload or
the outer envelope structure. Instead, each libp2p subystem that makes use of
signed envelopes will provide their own domain string when constructing the
envelope, and again when validating the envelope. If the domain string used to
validate is different from the one used to sign, the signature validation will
fail.

Domain strings may be any valid UTF-8 string, but MUST NOT contain the `:`
character (UTF-8 code point `0x3A`), as this is used to separate the domain
string from the content when signing.

## Wire Format

Since we already have a [protobuf definition for public keys][peer-id-spec], we
can use protobuf for this as well and easily embed the key in the envelope:


```protobuf
message SignedEnvelope {
  PublicKey publicKey = 1; // see peer id spec for definition
  bytes contents = 2;      // payload
  bytes signature = 3;     // signature of domain string + contents
}
```

The `publicKey` field contains the public key whose secret counterpart was used
to sign the message. This MUST be consistent with the peer id of the signing
peer, as the recipient will derive the peer id of the signer from this key.


## Signature Production / Verification

When signing, a peer will prepare a buffer by concatenating the following:

- The [domain separation string](#domain-separation), encoded as UTF-8
- The UTF-8 encoded `:` character
- The `contents` field

Then they will sign the buffer according to the rules in the [peer id
spec][peer-id-spec] and set the `signature` field accordingly.

To verify, a peer will "inflate" the `publicKey` into a domain object that can
verify signatures, prepare a buffer as above and verify the `signature` field
against it.

[addr-records-rfc]: ./0003-address-records.md
[peer-id-spec]: ../peer-ids/peer-ids.md
