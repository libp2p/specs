- Start Date: 2019-08-15
- Related issues: [go-ipfs/issues/5287](https://github.com/ipfs/go-ipfs/issues/5287), [multicodec/issues/130](https://github.com/multiformats/multicodec/issues/130), [go-libp2p-core/pull/41](https://github.com/libp2p/go-libp2p-core/pull/41)

# RFC 0001: Text Peer Ids as CIDs

## Abstract

This is an RFC to modify Peer Id spec to alter the default string representation
from Multihash to CIDv1 in Base32 and to support encoding/decoding text Peer Ids as CIDs.

[ipld-cid-spec]: https://github.com/ipld/cid

## Motivation

1.  Current text representation of Peer Id ([multihash][multihash] in [Base58btc][base58btc]) is case-sensitive.
    This means we can't use it in case-insensitive contexts such as domain names ([RFC1035][rfc1035] + [RFC1123][rfc1123]) or [FAT](fat) filesystems.
2.  [CID][ipld-cid-spec] provide [multibase][multibase] support and `base32`
    makes a [safe default][cidv1b32-move] that will work  in case-insensitive contexts,
    enabling us to put Peer Ids  [in domains][cid-in-subdomains] or create files with Peer Ids as names.
3.  It's much easier to upgrade wire protocols than text.
    This RFC makes Peer Ids in text form fully self describing, making them more future-proof.
    A dedicated [multicodec][multicodec] in text-encoded CID will indicate that [it's a hash of a libp2p public key][libp2p-key-multicodec].

[rfc1035]: http://tools.ietf.org/html/rfc1035
[rfc1123]: https://tools.ietf.org/html/rfc1123
[multibase]: https://github.com/multiformats/multibase/
[multicodec]: https://github.com/multiformats/multicodec
[multihash]: https://github.com/multiformats/multihash
[cid-in-subdomains]: https://github.com/ipfs/in-web-browsers/issues/89
[libp2p-key-multicodec]: https://github.com/multiformats/multicodec/issues/130
[cidv1b32-move]: https://github.com/ipfs/ipfs/issues/337
[base58btc]: https://en.bitcoinwiki.org/wiki/Base58#Alphabet_Base58
[fat]: https://en.wikipedia.org/wiki/Design_of_the_FAT_file_system

## Detailed design

1. Switch text encoding and decoding of Peer Ids from Multihash to [CID][ipld-cid-spec].
2. The new text representation should be CIDv1 with additional requirements:
    - MUST have [multicodec][multicodec] set to `libp2p-key` (`0x72`)
    - SHOULD have [multibase][multibase] set to `base32` (Base32 without padding, as specified by [RFC4648][rfc4648])

[rfc4648]: https://tools.ietf.org/html/rfc4648

### Backward compatibility

The old text representation (Multihash encoded as [`base58btc`][base58btc])
is a valid CIDv0 and does not require any special handling.

[base58btc]: https://en.bitcoinwiki.org/wiki/Base58#Alphabet_Base58

## Alternatives

We could just add a [multibase][multibase] prefix to multihash, but that requires more work and introduces a new format.
This option was rejected as using CID enables reuse of existing serializers/deserializers and does not create any new standards.

## Unresolved questions

This RFC punts pids-as-cids on the wire down the road but that's something we can revisit if it ever becomes relevant.

[go-libp2p-core-41]: https://github.com/libp2p/go-libp2p-core/pull/41
[libp2p-specs-111]: https://github.com/libp2p/specs/issues/111
