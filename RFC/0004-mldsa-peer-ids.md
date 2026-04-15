- Start Date: 2026-04-11
- Related PRs: [js-libp2p/pull/3432](https://github.com/libp2p/js-libp2p/pull/3432)
- Related Spec: [peer-ids/peer-ids.md](../peer-ids/peer-ids.md)

# RFC 0004: ML-DSA Key Support for libp2p Peer Identities

## Abstract

This RFC proposes adding support for post-quantum ML-DSA identity keys to
libp2p.

It defines a new `KeyType` value for ML-DSA in libp2p key protobufs, a wire
format for serializing ML-DSA public/private keys, and how peer IDs are derived
from ML-DSA public keys.

## Motivation

libp2p peer identities are currently based on classical signature schemes (RSA,
Ed25519, secp256k1, ECDSA).

To prepare libp2p identity and signature systems for post-quantum migration, we
need an interoperable encoding and verification story for ML-DSA keys.

Without a shared specification:

- Implementations may choose incompatible key encodings.
- Cross-implementation interoperability is not guaranteed.
- Future migration to hybrid or fully post-quantum deployments becomes harder.

## Design

### 1. `KeyType` extension

The key protobuf enum in the peer-id spec is extended with:

```protobuf
enum KeyType {
  RSA = 0;
  Ed25519 = 1;
  Secp256k1 = 2;
  ECDSA = 3;
  MLDSA = 4;
}
```

### 2. ML-DSA parameter sets

This RFC supports the three standardized ML-DSA parameter sets:

- `ML-DSA-44`
- `ML-DSA-65`
- `ML-DSA-87`

### 3. Key serialization in protobuf `Data`

For `PublicKey` and `PrivateKey` messages where `Type = MLDSA`, the `Data`
field is:

```
<variant-prefix><raw-key-bytes>
```

Where `variant-prefix` is one byte:

- `0x01` = `ML-DSA-44`
- `0x02` = `ML-DSA-65`
- `0x03` = `ML-DSA-87`

Raw key lengths are the standard ML-DSA key sizes for each variant:

- `ML-DSA-44`: public key `1312` bytes, expanded private key `2560` bytes
- `ML-DSA-65`: public key `1952` bytes, expanded private key `4032` bytes
- `ML-DSA-87`: public key `2592` bytes, expanded private key `4896` bytes

Implementations MUST reject malformed key payloads (unknown prefix,
missing prefix, or length mismatch).

### 4. Signature semantics

ML-DSA signatures are generated and verified using the standard ML-DSA
algorithm for the corresponding parameter set.

- Input to signing is the exact message bytes.
- No additional pre-hash step is applied by libp2p at the key API boundary.
- Verification is performed over the same message bytes with the same parameter
  set.

### 5. Peer ID derivation

Peer ID derivation remains unchanged:

1. Protobuf-encode `PublicKey` with `Type = MLDSA` and `Data` as specified
  above.
2. Compute peer ID multihash according to the existing rule:
   - identity multihash if encoded key is `<= 42` bytes
   - SHA-256 multihash otherwise

Because all ML-DSA public key encodings are much larger than 42 bytes, ML-DSA
peer IDs always use SHA-256 multihash.

## Backward Compatibility

- Existing peers and key types are unaffected.
- Implementations that do not support `KeyType = MLDSA` will reject those keys
  as unsupported.
- Text and CID peer ID formats are unchanged.

## Security Considerations

- This RFC only defines identity key representation and signature verification
  semantics.
- It does not by itself provide hybrid authentication or downgrade resistance
  between classical and post-quantum identities.
- Deployments should continue evaluating algorithm maturity, implementation
  quality, and runtime support in their target environments.

## Implementation Status (Non-Normative)

Current language support for ML-DSA is still evolving:

- Node.js runtime support is experimental.
- Browser WebCrypto support is unavailable.
- Go has an internal implementation for ML-DSA but no public API as of Go 1.26.

This RFC specifies interoperability behavior independent of implementation
maturity.
Production deployments SHOULD evaluate runtime support, performance, and audit
status before enabling ML-DSA identities.

## Open Questions

The following questions should be resolved before promoting this to a candidate
recommendation:

1. Default variant selection for new key generation (`ML-DSA-44`, `-65`, or
  `-87`).
2. Whether any libp2p subsystem should require dual-signature or hybrid
  identity strategies.
3. Whether to define mandatory test vectors in the peer-id spec for ML-DSA
  encodings.
4. Canonical private key format: should it be FIPS 204 expanded form ([multiformats/multicodec#399](https://github.com/multiformats/multicodec/pull/399), W3C DI Quantum-Safe Cryptosuite)?
