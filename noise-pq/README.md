| Lifecycle Stage | Maturity      | Status | Latest Revision |
|-----------------|---------------|--------|-----------------|
| 1A              | Working Draft | Active | 2026-06-24      |

Authors: [@paschal533](https://github.com/paschal533)

Interest Group: to be formed -- post on the [libp2p forum](https://discuss.libp2p.io) to join

See the [lifecycle document](https://github.com/libp2p/specs/blob/master/00-framework-01-spec-lifecycle.md) for context about the maturity level and expected evolution of this spec.

---

# Noise PQ: Post-Quantum Hybrid Noise Handshake for libp2p

**Protocol ID:** `/noise-mlkem768-hfs/0.1.0`
**Pattern:** `Noise_XXhfs_25519+ML-KEM-768_ChaChaPoly_SHA256`
**Based on:** [Noise HFS extension spec](https://github.com/noiseprotocol/noise_hfs_spec), [PQNoise (ePrint 2022/539)](https://eprint.iacr.org/2022/539), [NIST FIPS 203](https://doi.org/10.6028/NIST.FIPS.203)

## Table of Contents

- [1. Overview](#1-overview)
- [2. Algorithm Identifiers](#2-algorithm-identifiers)
- [3. Handshake Pattern](#3-handshake-pattern)
- [4. KEM Interface](#4-kem-interface)
- [5. Wire Format](#5-wire-format)
- [6. Token Ordering](#6-token-ordering)
- [7. State Machine](#7-state-machine)
- [8. Cipher State Split](#8-cipher-state-split)
- [9. ML-KEM Implicit Rejection](#9-ml-kem-implicit-rejection)
- [10. Security Properties](#10-security-properties)
- [11. Test Vectors](#11-test-vectors)
- [12. Usage](#12-usage)
- [13. Interoperability Requirements](#13-interoperability-requirements)
- [14. Reference Implementations](#14-reference-implementations)
- [15. Performance Reference](#15-performance-reference)

---

## 1. Overview

This document specifies the `Noise_XXhfs_25519+ML-KEM-768_ChaChaPoly_SHA256` handshake as a post-quantum hybrid extension of the classical [Noise XX](https://github.com/libp2p/specs/tree/master/noise) protocol used in libp2p.

The handshake adds an ephemeral KEM step (the Noise HFS tokens `e1` and `ekem1`) alongside the existing X25519 ECDH operations. This provides **hybrid post-quantum forward secrecy**: the session is secure if **either** the X25519 DH exchange **or** ML-KEM-768 is unbroken, preserving full backward compatibility with classical security guarantees while adding protection against future quantum adversaries.

The protocol uses raw ML-KEM-768 (NIST FIPS 203) as the KEM primitive in the `ekem1` slot. An earlier revision of this spec used X-Wing (a composite KEM combining ML-KEM-768 and X25519). X-Wing was replaced because the Noise XXhfs pattern already provides classical security through three independent Diffie-Hellman operations (`ee`, `es`, `se`). Using X-Wing in the `ekem1` slot would introduce a redundant X25519 computation inside the KEM, adding 64 bytes of wire overhead (32 bytes to the encapsulation key in Message A, 32 bytes to the ciphertext in Message B) with no security benefit. Raw ML-KEM-768 gives identical hybrid security guarantees with a smaller wire footprint.

---

## 2. Algorithm Identifiers

| Role | Algorithm | Specification |
|------|-----------|---------------|
| KEM | ML-KEM-768 | [NIST FIPS 203](https://doi.org/10.6028/NIST.FIPS.203) |
| DH | X25519 | RFC 7748 |
| AEAD | ChaCha20-Poly1305 | RFC 8439 |
| Hash / HKDF | SHA-256 | FIPS 180-4 / RFC 5869 |

ML-KEM-768 outputs a 32-byte shared secret. Its encapsulation key is 1,184 bytes and ciphertext is 1,088 bytes. Classical security is provided independently by the three X25519 DH operations built into the XXhfs pattern (`ee`, `es`, `se`), not by a composite KEM.

---

## 3. Handshake Pattern

The `XXhfs` pattern extends classical Noise XX by adding the `e1` and `ekem1` HFS tokens:

```
Noise_XXhfs_25519+ML-KEM-768_ChaChaPoly_SHA256:
  <- s
  ...
  -> e, e1
  <- e, ee, ekem1, s, es
  -> s, se
```

- **`e`**: X25519 ephemeral key (classical, 32 bytes)
- **`e1`**: ML-KEM-768 ephemeral encapsulation key (1,184 bytes)
- **`ekem1`**: ML-KEM-768 ciphertext encrypted under the `ee`-derived key (1,104 bytes: 1,088-byte ciphertext + 16-byte AEAD tag), followed by `MixKey(KEM shared secret)`

The HFS tokens follow the Noise HFS extension specification: `encryptAndHash(cipherText)` is applied **before** `mixKey(sharedSecret)`. This ordering is mandatory.

---

## 4. KEM Interface

Any KEM used with this protocol must implement the following interface:

```
IKem:
  PUBKEY_LEN: integer   // ML-KEM-768: 1184 bytes (encapsulation key)
  CT_LEN:     integer   // ML-KEM-768: 1088 bytes (ciphertext)
  SS_LEN:     integer   // ML-KEM-768: 32 bytes (shared secret)
  SK_LEN:     integer   // ML-KEM-768: 2400 bytes (decapsulation key)

  generateKemKeyPair() -> (publicKey: bytes[PUBKEY_LEN], secretKey: bytes[SK_LEN])
  encapsulate(remotePublicKey: bytes[PUBKEY_LEN]) -> (cipherText: bytes[CT_LEN], sharedSecret: bytes[SS_LEN])
  decapsulate(cipherText: bytes[CT_LEN], secretKey: bytes[SK_LEN]) -> sharedSecret: bytes[SS_LEN]
```

The default implementation uses ML-KEM-768 as defined in [NIST FIPS 203](https://doi.org/10.6028/NIST.FIPS.203). Implementations MAY substitute a different KEM conforming to this interface for testing or experimentation, but interoperability across implementations requires the ML-KEM-768 default.

---

## 5. Wire Format

Message sizes assume an empty libp2p `NoiseHandshakePayload`. Real handshakes include identity keys and signatures (approximately 108 bytes per side for Ed25519), adding roughly 308 bytes total to the figures below.

### 5.1 Message A (initiator to responder)

```
+-------------------+-----------------------+---------+
| e.publicKey       | e1.publicKey          | payload |
| 32 bytes          | 1184 bytes            | 0 bytes |
+-------------------+-----------------------+---------+
Total: 1216 bytes
```

`e.publicKey` is sent in plaintext (no cipher key exists yet). `e1.publicKey` is processed via `encryptAndHash()`, which at this stage is a plain `MixHash()` because there is no active cipher.

### 5.2 Message B (responder to initiator)

```
+-------------------+-----------------------+--------------------+---------+
| e.publicKey       | enc(KEM ciphertext)   | enc(s.publicKey)   | payload |
| 32 bytes          | 1104 bytes            | 48 bytes           | 16 bytes|
+-------------------+-----------------------+--------------------+---------+
Total: 1200 bytes (with empty payload; 16-byte AEAD tag on payload)
```

After `ee`: `MixKey(DH(e_R, e_I))` establishes the first cipher key. The 1,088-byte ML-KEM-768 ciphertext is encrypted under this key (adding a 16-byte AEAD tag = 1,104 bytes total). `MixKey(kemSharedSecret)` follows the ciphertext, strengthening subsequent operations.

### 5.3 Message C (initiator to responder)

```
+--------------------+---------+
| enc(s.publicKey)   | payload |
| 48 bytes           | 16 bytes|
+--------------------+---------+
Total: 64 bytes (with empty payload)
```

Identical structure to the classical Noise XX Message C.

### 5.4 Size comparison with classical XX

| Message | Classical XX | XXhfs (PQ) | Delta |
|---------|------------:|----------:|------:|
| Msg A | 32 bytes | 1,216 bytes | +1,184 bytes |
| Msg B | 96 bytes | 1,200 bytes | +1,104 bytes |
| Msg C | 64 bytes | 64 bytes | 0 bytes |
| **Total** | **192 bytes** | **2,480 bytes** | **+2,288 bytes** |

---

## 6. Token Ordering

The `ekem1` token **must** follow this exact ordering on both initiator and responder sides:

**Responder (write ekem1):**

```
1. (ct, ss) = encapsulate(re1)       // encapsulate to initiator's e1 encapsulation key
2. encryptAndHash(ct)                // encrypt ciphertext under ee-derived key
3. mixKey(ss)                        // mix KEM shared secret AFTER encrypting ct
```

**Initiator (read ekem1):**

```
1. ct = decryptAndHash(enc_ct)       // decrypt the ciphertext (AEAD authenticated)
2. ss = decapsulate(ct, e1.secretKey)
3. mixKey(ss)                        // must match write ordering
```

Swapping steps 2 and 3 (encrypt/decrypt after mixKey) produces divergent chaining keys and is **incorrect**. The AEAD protection on the ciphertext means tampering is caught at step 1 before decapsulation is attempted.

---

## 7. State Machine

```
Initiator                               Responder
---------                               ---------
generate e (X25519)
generate e1 (ML-KEM-768)
writeMessageA(payload=empty)
  MixHash(e.publicKey)
  MixHash(e1.publicKey)
  -> e, e1
                                        readMessageA()
                                          MixHash(e.publicKey)    // store as re
                                          MixHash(e1.publicKey)   // store as re1

                                        generate e (X25519)
                                        writeMessageB(payload)
                                          MixHash(e.publicKey)
                                          ee: MixKey(DH(e_R, e_I))
                                          (ct, ss) = encapsulate(re1)
                                          encryptAndHash(ct)      // ekem1 write
                                          mixKey(ss)
                                          encryptAndHash(s.publicKey)
                                          es: MixKey(DH(s_R, e_I))
                                          encryptAndHash(payload)
                                          -> e, enc(ct), enc(s), enc(payload)

readMessageB()
  MixHash(re.publicKey)
  ee: MixKey(DH(e_I, re))
  ct = decryptAndHash(enc_ct)         // ekem1 read
  ss = decapsulate(ct, e1.secretKey)
  mixKey(ss)
  resp_s = decryptAndHash(enc_s)
  es: MixKey(DH(e_I, resp_s))
  verify payload signature

writeMessageC(payload)
  encryptAndHash(s.publicKey)
  se: MixKey(DH(s_I, re))
  encryptAndHash(payload)
  -> enc(s), enc(payload)
                                        readMessageC()
                                          init_s = decryptAndHash(enc_s)
                                          se: MixKey(DH(e_R, init_s))
                                          verify payload signature

[cs1, cs2] = split()                    [cs1, cs2] = split()
encrypt = cs1, decrypt = cs2            encrypt = cs2, decrypt = cs1
```

---

## 8. Cipher State Split

After `split()`, two directional cipher states are derived from the final chaining key via HKDF-SHA256:

| Direction | Initiator | Responder |
|-----------|-----------|-----------|
| Initiator to responder | encrypt with `cs1` | decrypt with `cs1` |
| Responder to initiator | decrypt with `cs2` | encrypt with `cs2` |

Each cipher state maintains an independent nonce counter starting at zero. The nonce is never transmitted; both sides increment in lockstep.

---

## 9. ML-KEM Implicit Rejection

ML-KEM-768 (FIPS 203 Section 6.4) implements implicit rejection: `Decaps()` never throws on an invalid ciphertext. Instead it returns a pseudorandom value derived from a secret implicit rejection key. This means:

- A tampered or wrong-key ciphertext produces a divergent KEM shared secret rather than an explicit error.
- The divergence propagates through `mixKey()`, causing all subsequent AEAD operations to fail authentication.
- The handshake still aborts cleanly via AEAD failure.

Because `encryptAndHash(ct)` precedes `mixKey(ss)`, an attacker who tampers with the ciphertext in transit will be caught by the AEAD tag before decapsulation runs.

---

## 10. Security Properties

| Property | Mechanism |
|----------|-----------|
| Forward secrecy (classical) | Ephemeral X25519 on both sides (DH `ee`), plus `es` and `se` |
| Forward secrecy (quantum-safe) | Ephemeral ML-KEM-768 (`ekem1` token, FIPS 203) |
| Mutual authentication | DH(`es`) + DH(`se`) via libp2p identity signatures |
| Identity hiding | Static keys transmitted after ephemeral exchange |
| Hybrid robustness | Secure if either X25519 (DH tokens) or ML-KEM-768 is unbroken |
| Payload confidentiality | ChaCha20-Poly1305 under the post-split cipher states |

Classical security is provided by the three independent X25519 DH operations built into the XXhfs pattern. The `ekem1` slot carries only the ML-KEM-768 component. This separation means neither component's failure degrades the other's contribution to the chaining key.

**Out of scope:** Quantum-safe *authentication*. Identity keys use Ed25519 (classical). Full post-quantum authentication requires ML-DSA (FIPS 204) identity keys and is tracked separately.

---

## 11. Test Vectors

Implementations should validate against the test vectors schema:

```json
{
  "protocol": "Noise_XXhfs_25519+ML-KEM-768_ChaChaPoly_SHA256",
  "vectors": [
    {
      "vector_index": 1,
      "static_i_public":        "<hex 32B>",
      "static_i_private":       "<hex 32B>",
      "static_r_public":        "<hex 32B>",
      "static_r_private":       "<hex 32B>",
      "ephemeral_dh_i_public":  "<hex 32B>",
      "ephemeral_dh_i_private": "<hex 32B>",
      "ephemeral_dh_r_public":  "<hex 32B>",
      "ephemeral_dh_r_private": "<hex 32B>",
      "ephemeral_kem_i_public": "<hex 1184B>",
      "ephemeral_kem_i_secret": "<hex 2400B>",
      "encap_seed_hex":         "<hex 32B>",
      "msg_a":                  "<hex 1216B>",
      "msg_b":                  "<hex 1200B>",
      "msg_c":                  "<hex 64B>",
      "handshake_hash":         "<hex 32B>",
      "cs1_k":                  "<hex 32B>",
      "cs2_k":                  "<hex 32B>"
    }
  ]
}
```

Reference test vectors are published in the JavaScript implementation at [ChainSafe/js-libp2p-noise PR #665](https://github.com/ChainSafe/js-libp2p-noise/pull/665) under `test/fixtures/pqc-test-vectors.json`. These vectors have been validated against all three reference implementations (TypeScript, Python, Rust).

---

## 12. Usage

### JavaScript (js-libp2p-noise)

```typescript
import { createLibp2p } from 'libp2p'
import { noiseHFS, noise } from '@chainsafe/libp2p-noise'

const node = await createLibp2p({
  connectionEncrypters: [noiseHFS(), noise()], // HFS preferred; falls back to classical
})
```

### Python (py-libp2p)

```python
from libp2p.security.noise.pq.transport_pq import TransportPQ, PROTOCOL_ID
# PROTOCOL_ID = "/noise-mlkem768-hfs/0.1.0"

host = await new_node(
    security_opt={PROTOCOL_ID: TransportPQ(libp2p_keypair, noise_privkey)}
)
```

---

## 13. Interoperability Requirements

A conforming implementation MUST:

1. Use the exact protocol name string: `Noise_XXhfs_25519+ML-KEM-768_ChaChaPoly_SHA256`
2. Use raw ML-KEM-768 (FIPS 203) as the KEM primitive — not X-Wing or any other composite wrapper
3. Apply `encryptAndHash(cipherText)` BEFORE `mixKey(sharedSecret)` in the `ekem1` token
4. Transmit `e1.publicKey` as exactly 1,184 bytes in Message A (no AEAD tag at this stage)
5. Transmit `ekem1` as exactly 1,104 bytes in Message B (1,088-byte ciphertext + 16-byte AEAD tag)
6. Use the libp2p protocol identifier `/noise-mlkem768-hfs/0.1.0` for multistream negotiation
7. Pass the test vectors published by the reference implementation

---

## 14. Reference Implementations

Three independent implementations have been developed and validated against each other:

| Language | Repository | Status |
|----------|-----------|--------|
| TypeScript | [ChainSafe/js-libp2p-noise PR #665](https://github.com/ChainSafe/js-libp2p-noise/pull/665) | Open PR; 99 tests, 5 deterministic test vectors |
| Python | [libp2p/py-libp2p PR #1310](https://github.com/libp2p/py-libp2p/pull/1310) | Open PR; 68 tests |
| Rust | [royzah/rust-libp2p PR #1](https://github.com/royzah/rust-libp2p/pull/1) | Open PR; uses `ml-kem` crate (RustCrypto) |

### Triangle Interoperability Test (2026-06-24)

A 3-way pairwise interoperability test was conducted over real TCP connections between all three implementations on a single Windows 11 Pro x64 machine:

| Pair | Listener | Dialer | Result |
|------|----------|--------|--------|
| JS ↔ Python | TypeScript (Node.js v22) | Python 3.13.1 | ✅ PASS |
| Rust ↔ JS | Rust | TypeScript (Node.js v22) | ✅ PASS |
| Rust ↔ Python | Rust | Python 3.13.1 | ✅ PASS |

In each test both sides completed the full three-message XXhfs handshake, then exchanged an encrypted transport message. All three pairs passed, confirming that the protocol specification is precise enough for independent implementors across three language ecosystems to achieve bit-for-bit wire compatibility.

---

## 15. Performance Reference

Measured on Node.js v22, Windows 11 x64 (pure-JS backend, `@noble/post-quantum`):

| Operation | ops/s | ms/op |
|-----------|------:|------:|
| ML-KEM-768 keygen | 293 | 3.42 |
| ML-KEM-768 encapsulate | 120 | 8.32 |
| ML-KEM-768 decapsulate | 136 | 7.33 |
| KEM round-trip | 47 | 21.43 |
| Classical XX handshake | 114 | 8.75 |
| XXhfs handshake (pure-JS) | 23 | 44.18 |
| XXhfs handshake (WASM KEM) | 23 | 42.80 |

The approximately 5x latency increase over classical XX is dominated by the ML-KEM-768 KEM round-trip (~21 ms). A Rust WASM backend accelerates isolated KEM throughput 3.2x; full handshake improvement is approximately 4% because non-KEM operations (SHA-256, ChaCha20-Poly1305, HKDF, Ed25519, protobuf serialization, async scheduling) dominate in the JavaScript runtime.

Python measurements with the `kyber-py` pure-Python backend: keygen ~10.5 ms, encap ~12.3 ms, decap ~15.5 ms; KEM accounts for approximately 63% of total handshake time (42.96 ms). A single substitution to the `liboqs` C backend is predicted to reduce total latency to approximately 16 ms.
