| Lifecycle Stage | Maturity      | Status | Latest Revision |
|-----------------|---------------|--------|-----------------|
| 1A              | Working Draft | Active | 2026-09-17      |

Authors: [@paschal533](https://github.com/paschal533)

Interest Group: to be formed -- post on the [libp2p forum](https://discuss.libp2p.io) to join

See the [lifecycle document](https://github.com/libp2p/specs/blob/master/00-framework-01-spec-lifecycle.md) for context about the maturity level and expected evolution of this spec.

---

# Noise PQ: Post-Quantum Hybrid Noise Handshake for libp2p

**Protocol ID:** `/noise-mlkem768-hfs/0.2.0`
**Pattern:** `Noise_XXhfs_25519+MLKEM768_ChaChaPoly_SHA256`
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

This document specifies the `Noise_XXhfs_25519+MLKEM768_ChaChaPoly_SHA256` handshake as a post-quantum hybrid extension of the classical [Noise XX](https://github.com/libp2p/specs/tree/master/noise) protocol used in libp2p.

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

### 2.1 Protocol name

Earlier revisions of this spec named the protocol `Noise_XXhfs_25519+ML-KEM-768_ChaChaPoly_SHA256`. That is not a valid Noise protocol name: [Noise revision 34, §8.2](https://noiseprotocol.org/noise.html) requires each algorithm name to consist solely of alphanumeric characters and `/`. The KEM is therefore named `MLKEM768`, giving `Noise_XXhfs_25519+MLKEM768_ChaChaPoly_SHA256`. Thanks to [@royzah](https://github.com/royzah) for spotting this.

The rename is wire-incompatible. The name is 44 bytes, longer than HASHLEN (32), so `InitializeSymmetric` sets `h = HASH(protocol_name)` and `ck = h`; peers using the old and new names derive different keys and the handshake fails when the initiator decrypts Message B. The libp2p protocol identifier therefore moved from `/noise-mlkem768-hfs/0.1.0` to `/noise-mlkem768-hfs/0.2.0`. Message sizes are unchanged.

[libp2p/specs#727](https://github.com/libp2p/specs/pull/727), by @royzah, already uses the `MLKEM768` protocol name, with the identifier `/noise-mlkem768-hfs/0.1.0`.

---

## 3. Handshake Pattern

The `XXhfs` pattern extends classical Noise XX by adding the `e1` and `ekem1` HFS tokens:

```
Noise_XXhfs_25519+MLKEM768_ChaChaPoly_SHA256:
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

Each test vector has the following form. The example is vector 1 of the reference fixture, copied exactly:

```json
{
  "protocol": "Noise_XXhfs_25519+MLKEM768_ChaChaPoly_SHA256",
  "vectors": [
    {
      "vector_index": 1,
      "description": "Noise_XXhfs vector 1: all keys seeded from base byte 0x10",
      "static_i_public": "7b4e909bbe7ffe44c465a220037d608ee35897d31ef972f07f74892cb0f73f13",
      "static_i_private": "1111111111111111111111111111111111111111111111111111111111111111",
      "static_r_public": "052a50773ac8d91773f2dc9662e12f0defe915e415b8a1c8e20a5a3d6ab2b843",
      "static_r_private": "1212121212121212121212121212121212121212121212121212121212121212",
      "ephemeral_dh_i_public": "197fc2c567dc03ee2aadf0ed86681dac24daa76e83ca555875dd3be7376e5306",
      "ephemeral_dh_i_private": "1313131313131313131313131313131313131313131313131313131313131313",
      "ephemeral_dh_r_public": "18a6f8c1a7fddf22bd410138f79f7298cd38d1d0a542d4266d556be8609d8862",
      "ephemeral_dh_r_private": "1414141414141414141414141414141414141414141414141414141414141414",
      "ephemeral_kem_i_public": "b989c17f78bdfc62afa2c0855471be97c9a287ecab608b84214551254286b72b8bcb69bad00b73dd322fb0f2a9671a8b7b18cc614cbf0f990ee8fb0e7c2c8e171122ca148652e809ff140969d713ef918fc2b7167c50a1c260a9fa6980a77639200c187d7648f017bec292859dd57b391b8d4bc6a2de0c9b354c0b6b6a64f10b5e91c17471f771a679634c5c222a533dd59564d0084aeb91be41436ac6a60705da9336d02e6642317c886c71e47509f6673a2bcbadb87d4aa11876f5611af978cb851ae4b1415b038a7874b3e10a2fbe3091b9b64af51bb20554c6ed6bc678f905a1f1b6121c62cbbacb74ca6afba594ec384166b4cf1cb78656786cbd51b1c5664de6f36ef265a331718432179abb907b0fb588d6e7635ef66c6083c4700567f8e82814a22bba13976bb997d0f72c01312a82f15c4aaa4fcbfbb4bf1b2bd640c5bbf18813906db4946065e14a77115cd80216f238025f712113e100f65b06eb358e53a33020b698c2a1298f320f7a9b290ce495eff041bfc972c123c2609891eae2810365373b3b9a42210702c7b514b207b57a03eb7643b566099e0aa3d5288823b9a2fcb4a9ea7ba3d26c9e9bf6823304b1938ab7bfe23e4f24469d4820f9b17353864338462650c0922bc57b507cb0e5dc014b1806383432b16b34a7f311a557c39025140763907d88caca8a923708239c699203e7bacc908ed75b4835943fcdf79f0ce2484786b5b725560e8b99951b4996f475a5cb309e37ba08970447f3a8bc651ce00a4ac6cc48dfd0289b89a00f006e9a138d5d923b24bb6411f9a33b756a041985ca4c481d7a838d3082f0b791a44139c2c1b7e6166ae9f37cef82469cfa7b1dd00bd23bbdf0e1ac15fc19d27155b690858ee32be8295232676b8ceb49c601aea6098747c6c94bc767d21141e0940aab2016c3a8be8ddb345997491ebc5e86471ad58c84d0a69fd0ac55cdd25ce6085144f29ce397203533c3f5d9c466a1a7b71c9738567b3cdabd3969bd14087d3165765c22cf66a03a89759124e48528631168430212c5860fd874c8d53e61cb91f843a6ede17fea41010a217b32d519d7ca52e9a1169e71c4cf036de8c63476a65bd2095bc27c81166200d387c5eacbb797c83003fb56545ba1f17233a63c25d884c21e393ece3a7fe8f07a9ac2c426cb82a112744a7a81762190dd738e73c854e8e00d0cb57ec9f25104a330011283f1408172e43dcb6345de854daee1ac8fb447436024b15803b21bb0b15c35fc7190eb3a026b04b68dfa81f4467ff90a75c0a6aa530c39668565d1152752e9c15eac322794a49e9c8998f614a9c59ce2335f9fc742377587860b9b22f4c201cc86518c1780648c3950a80977b6bc396b3e654415323b844ba0081762c0a13632218eda177c7cc09bd791a157b3a8fb21be620ba2fbe551019ccd22870ddf8340b4c67817ac90437b71b38b6c25e054f750c39e0666675c256f961b54a49e9925b39611bbddeb4d9c5316ebf7cb600ca3b6a486c4e7b1de809839d63945e203011a16d1118280f7242e148ed214c0e68588afa93d42c17813e64510281f73cab346493c3e7740330a6ea20973781ac73a78664bf80471f7526155c923f72ab656b007450a106e2e9eefac5c56647bce316a7164a81f32dfee0fd2d397649d",
      "ephemeral_kem_i_secret": "11858da29518efab7e940865c4294624fc4c4040906a92c9fac677fd4312bdfb5917c364cdb82abfe4c230e658dd8c014d5c7ccae8b219fa5d62c208bc5022bfc61d19646e998388d4b7c5383899cb04c98b0539b740b37b5727ada94ed500a2d571bbfcc78dfc216a81c23338228d655705cd375a747a1d17793902cc6774171baa879fcfe1987e43ae48d6bd7d8563edd9af116500e37a8dbcc3cc072551f1d14ec8b61e9987ca8506a6cdc22eb19c71ee8bce96021666da4b21faa987b13625c95f682561d9c4436742157d75a0482551b3606d303278a4f6cc8055ae6f2941cc9733c9f12ff14276eb7137edeb0237ba6a9d81b25b53c1a6e77a94236762dac94df26b84328a85f26b86723d289a1ef22648ec61b28e49b3d927cd0ad8a31fa53378152100fb67f64285df909aee9b141e5a603129c72d64aedea20aed6b3cbefac8ba294edf537817a46dcc24529b350a6f26314fe59b3f43cc00a5bb00b001820a70f145484d270331ca789cf7b5ab5c4a35a8a87341b64b432f1a545b66d1a316cb7b2e333dcbf8140a5a7336cccfa1cc1eaa9184b6e476bdbb7fdc125f89d0ade8cabec6101970cc5b4b108a75395fa6544a9b5768212b320bbb05f6934fc035b0a5dca46a245b02a863875ba141986526494272f07ecbea6895f43dece7bc0b838ce345101f49235714394d922dc8436898a94e5cd5a7170c6e83e208aed99d824a80f99ab2c1795a83dc3fc923a33be835de641222a8a222c276369272576b36bcb57c5680818c84666711827f2b3ad87bce5cc394efa479bea965dc206459271ac04b1918bc8be097012543120e89220119b653939b08d57eaef4392815a616d607a91b9ef5a367c80b8c2ea0281d58b81ab62ff191021aeb021769879fe65811304516803580900043e612786c8ddcb807d94805c09682dd124c784661f86ba95220104d700de1f440dc5339da41ba1b9c3d09b34c6d6c76b74517e034aed8377baed73e3754a534b5a7b1eb957adb74a0460f5c42218bc62400076681090042c0a9bed67f6236b0a4ca11024bcc6c645ced6463343a13f1aa8621205c21579aed116c01b1be9e366057482eec6ca23bb091a1345d87660574c13c94aa1b64716cdcfac2c166c8e71b205f7ca715d722166131ffc0a5b954948f85c857e89ca9301ce959a9c9c0a8c978422c2093389a5d3cdb2abc4c68e33253f98b20834ac9de8a66666211779b066c372c2fb53d82041c5e937ae9d7c395c670d880cd2330cfe6cba8ed25421d555283144ded464839160258169964f47bb9473669e36b35413120884619a777b2e2ca702ca04db83f5a729e36cb4be0001960c7c33c60cd4025b74453647f318df2a1116b0968af643b24a3b1c0d7097187b368716460399c1f8b779f1b801ea95ddef26c12238c377baf7490cbc2d301cbe378b9195977d6bee7aacbf86b386b01a6cc7909054849ef156d09657047e32fe2644d9531a0cda6a8d7134e36178ba1ab975875bc0d5899aaa52969195b91008ea0d078ae71cc612aa6753021a8966a83d555ae62ba6512470bdcb673124afdd4cda990c4b9639250c53c35d000b2293e9e80a46ee88337d789f03c2de2d765b989c17f78bdfc62afa2c0855471be97c9a287ecab608b84214551254286b72b8bcb69bad00b73dd322fb0f2a9671a8b7b18cc614cbf0f990ee8fb0e7c2c8e171122ca148652e809ff140969d713ef918fc2b7167c50a1c260a9fa6980a77639200c187d7648f017bec292859dd57b391b8d4bc6a2de0c9b354c0b6b6a64f10b5e91c17471f771a679634c5c222a533dd59564d0084aeb91be41436ac6a60705da9336d02e6642317c886c71e47509f6673a2bcbadb87d4aa11876f5611af978cb851ae4b1415b038a7874b3e10a2fbe3091b9b64af51bb20554c6ed6bc678f905a1f1b6121c62cbbacb74ca6afba594ec384166b4cf1cb78656786cbd51b1c5664de6f36ef265a331718432179abb907b0fb588d6e7635ef66c6083c4700567f8e82814a22bba13976bb997d0f72c01312a82f15c4aaa4fcbfbb4bf1b2bd640c5bbf18813906db4946065e14a77115cd80216f238025f712113e100f65b06eb358e53a33020b698c2a1298f320f7a9b290ce495eff041bfc972c123c2609891eae2810365373b3b9a42210702c7b514b207b57a03eb7643b566099e0aa3d5288823b9a2fcb4a9ea7ba3d26c9e9bf6823304b1938ab7bfe23e4f24469d4820f9b17353864338462650c0922bc57b507cb0e5dc014b1806383432b16b34a7f311a557c39025140763907d88caca8a923708239c699203e7bacc908ed75b4835943fcdf79f0ce2484786b5b725560e8b99951b4996f475a5cb309e37ba08970447f3a8bc651ce00a4ac6cc48dfd0289b89a00f006e9a138d5d923b24bb6411f9a33b756a041985ca4c481d7a838d3082f0b791a44139c2c1b7e6166ae9f37cef82469cfa7b1dd00bd23bbdf0e1ac15fc19d27155b690858ee32be8295232676b8ceb49c601aea6098747c6c94bc767d21141e0940aab2016c3a8be8ddb345997491ebc5e86471ad58c84d0a69fd0ac55cdd25ce6085144f29ce397203533c3f5d9c466a1a7b71c9738567b3cdabd3969bd14087d3165765c22cf66a03a89759124e48528631168430212c5860fd874c8d53e61cb91f843a6ede17fea41010a217b32d519d7ca52e9a1169e71c4cf036de8c63476a65bd2095bc27c81166200d387c5eacbb797c83003fb56545ba1f17233a63c25d884c21e393ece3a7fe8f07a9ac2c426cb82a112744a7a81762190dd738e73c854e8e00d0cb57ec9f25104a330011283f1408172e43dcb6345de854daee1ac8fb447436024b15803b21bb0b15c35fc7190eb3a026b04b68dfa81f4467ff90a75c0a6aa530c39668565d1152752e9c15eac322794a49e9c8998f614a9c59ce2335f9fc742377587860b9b22f4c201cc86518c1780648c3950a80977b6bc396b3e654415323b844ba0081762c0a13632218eda177c7cc09bd791a157b3a8fb21be620ba2fbe551019ccd22870ddf8340b4c67817ac90437b71b38b6c25e054f750c39e0666675c256f961b54a49e9925b39611bbddeb4d9c5316ebf7cb600ca3b6a486c4e7b1de809839d63945e203011a16d1118280f7242e148ed214c0e68588afa93d42c17813e64510281f73cab346493c3e7740330a6ea20973781ac73a78664bf80471f7526155c923f72ab656b007450a106e2e9eefac5c56647bce316a7164a81f32dfee0fd2d397649db93f671ec40f1267e7ecc81ba07fc9b9c2375b9680a9234e2d48bddf359b759f1515151515151515151515151515151515151515151515151515151515151515",
      "encap_seed_hex": "1616161616161616161616161616161616161616161616161616161616161616",
      "prologue": "",
      "msg_a": "197fc2c567dc03ee2aadf0ed86681dac24daa76e83ca555875dd3be7376e5306b989c17f78bdfc62afa2c0855471be97c9a287ecab608b84214551254286b72b8bcb69bad00b73dd322fb0f2a9671a8b7b18cc614cbf0f990ee8fb0e7c2c8e171122ca148652e809ff140969d713ef918fc2b7167c50a1c260a9fa6980a77639200c187d7648f017bec292859dd57b391b8d4bc6a2de0c9b354c0b6b6a64f10b5e91c17471f771a679634c5c222a533dd59564d0084aeb91be41436ac6a60705da9336d02e6642317c886c71e47509f6673a2bcbadb87d4aa11876f5611af978cb851ae4b1415b038a7874b3e10a2fbe3091b9b64af51bb20554c6ed6bc678f905a1f1b6121c62cbbacb74ca6afba594ec384166b4cf1cb78656786cbd51b1c5664de6f36ef265a331718432179abb907b0fb588d6e7635ef66c6083c4700567f8e82814a22bba13976bb997d0f72c01312a82f15c4aaa4fcbfbb4bf1b2bd640c5bbf18813906db4946065e14a77115cd80216f238025f712113e100f65b06eb358e53a33020b698c2a1298f320f7a9b290ce495eff041bfc972c123c2609891eae2810365373b3b9a42210702c7b514b207b57a03eb7643b566099e0aa3d5288823b9a2fcb4a9ea7ba3d26c9e9bf6823304b1938ab7bfe23e4f24469d4820f9b17353864338462650c0922bc57b507cb0e5dc014b1806383432b16b34a7f311a557c39025140763907d88caca8a923708239c699203e7bacc908ed75b4835943fcdf79f0ce2484786b5b725560e8b99951b4996f475a5cb309e37ba08970447f3a8bc651ce00a4ac6cc48dfd0289b89a00f006e9a138d5d923b24bb6411f9a33b756a041985ca4c481d7a838d3082f0b791a44139c2c1b7e6166ae9f37cef82469cfa7b1dd00bd23bbdf0e1ac15fc19d27155b690858ee32be8295232676b8ceb49c601aea6098747c6c94bc767d21141e0940aab2016c3a8be8ddb345997491ebc5e86471ad58c84d0a69fd0ac55cdd25ce6085144f29ce397203533c3f5d9c466a1a7b71c9738567b3cdabd3969bd14087d3165765c22cf66a03a89759124e48528631168430212c5860fd874c8d53e61cb91f843a6ede17fea41010a217b32d519d7ca52e9a1169e71c4cf036de8c63476a65bd2095bc27c81166200d387c5eacbb797c83003fb56545ba1f17233a63c25d884c21e393ece3a7fe8f07a9ac2c426cb82a112744a7a81762190dd738e73c854e8e00d0cb57ec9f25104a330011283f1408172e43dcb6345de854daee1ac8fb447436024b15803b21bb0b15c35fc7190eb3a026b04b68dfa81f4467ff90a75c0a6aa530c39668565d1152752e9c15eac322794a49e9c8998f614a9c59ce2335f9fc742377587860b9b22f4c201cc86518c1780648c3950a80977b6bc396b3e654415323b844ba0081762c0a13632218eda177c7cc09bd791a157b3a8fb21be620ba2fbe551019ccd22870ddf8340b4c67817ac90437b71b38b6c25e054f750c39e0666675c256f961b54a49e9925b39611bbddeb4d9c5316ebf7cb600ca3b6a486c4e7b1de809839d63945e203011a16d1118280f7242e148ed214c0e68588afa93d42c17813e64510281f73cab346493c3e7740330a6ea20973781ac73a78664bf80471f7526155c923f72ab656b007450a106e2e9eefac5c56647bce316a7164a81f32dfee0fd2d397649d",
      "msg_b": "18a6f8c1a7fddf22bd410138f79f7298cd38d1d0a542d4266d556be8609d886271fa9be2c46cc471c8d370b63d9a60259c4fa6f560b8853e5254238cb13f245424bc09033e258232dd81d2d53f5790ce34d62d6720f029ff8e63fb078f4cda36d9520e4c72b73a2be66ca09ef33d56dbbcef858c094a7af50f43021733ebc799a184c1e976328bc1033685e1f1684396338c12fb995055b1beef613ef73edd50a1c8d71cb6bfcb14c8db611863059c4d1e876168e96f8e05c3a27598dfd57b51a1883ca90fd262bd61977b53094aa1e3b5cb9967629f534dc6e24f2570b8cbd21fd361f1dc3ad8ae178bf6996d0b1eea239cd3651b0c9ad60c35ded7cebefb65736cee5f49521cd1c309c80898a16dfeeefb5fe048a12fcb1c85e46b3417a87c29330d0653f15205e31c0ac8895f064bfc7d7f9d9f825833b8241f79738b8d470520b54b4bc020cf815a2a2c8ea727c6f8d8ecd3661543a9744557a3ba6ad8a025636495b50622e12c4c506e45ed0a80d7a1f127a7f8f0be140a49ac37ae74ed6f432d06777a1e48b6107cf670683a0fd2995c3cfb77aecf52b09819e91e8fa23388f10883e2041525ae3baeecd460d8a96a0f86098a6c24331edcc1949d57b26f6b8e0f5597875f166660dd3f012c6d1ae9445b5a7d404184bad59ec3159df2c5e2d16c1aef9788055c6e01d52f70fcd7841ee7b6ed5667a00ba1d9c067e61f9b021f7e244063f4aa385e04d6137c0223fcf7c61559aa09faf82291e42a5e6667d3dd61bd5bb28c6fa550ec98fef0f922265e95a4711ea67cd03bcdd987af5b025c488c1b38b4a1aed911b5739c00cabc64f94ce7e728ba07ec5ead211b43f8c0cc851854d0f011841809c170a959e3ecdcd69e8addb6104058e0a6a2881c719dc04cbe94e9615f95028c64b93a632ffa0f93acc153d8aab120a6279f935d4768dc1140e7eacb5aec319ceec293a9be3715602aff5734073e4f4cb3082eb107d1c5eb312b2906c9ecfa4a859664ba352a6b2044dd01537947a5aaa46f6dc9994eec0abf0fc6d3e9d08130e278617c4453317fc917a48a9f72b67e151e5cc0b0be6730663aa4d273a9ed4a116cd365d54e1660b0091cff450de68a50eb1a5fa1ad60a46bd28670e4289c655fc7d23e04ca44737b208d9cb62ffd37345681ab9ee9f071c9a02b510985ea928302f7bba9d1cd5b9c627d75606a5dafe978cf1b4cfcfe4a920daf5247ce82d60aa75e903231caa1b5fd6790692bdf16e7691baad701187b2e9bfa5e13806dea35f4b9b8321a3780d718b3243d04269ef97af07c58e844db9bcc9137661d3d2080d962b37b522cd27b9e78e8d5a3db47c8e8251b58dc63b10b02c00c19d6317bf9bd47985b921d62f2b4f89e9d4720c6d4ba531b15cbb0a5ace1bac607a1143b3a706b321fd9f341a827d1d949753fe673e193a5efd7111291a52c2ae8d07f8da8cea2989786cc74021e1d869b0140db1d2ccc1231480929bef97e2a82b0ed2a7d6e4a83bfc423d3a6849064c196ce770889290f37e4de90d793959ba1643089977878ddbf9a0434e78c761aebd5d1f6961c7c37f052bc6f8b16abc08757f0eb5979d0f7ead2f232c6d8109d90bc49adc638f17272a1bd4cc69a570496131c6340bd0b82baca26e4d70b25996a8ccd5817136db7d3b7ade97ee11b11eb2c6f61b2efc01f62",
      "msg_c": "ecee945a65a96f34fdaf116d3c70727852b0a25eb350bf72bb088f21cb374ba50c973fdc4ea63d2065ac9ff9fb347f0700dcf7ec3bb3a3c01f84290c6d8931aa",
      "msg_a_bytes": 1216,
      "msg_b_bytes": 1200,
      "msg_c_bytes": 64,
      "handshake_hash": "b5a3c9854777aa5dad0a633c769bcc6662713f20f14e0371e4bfd253e1869eef",
      "cs1_k": "0a825d67cbf14170dcccf6f5c54d50f46a9a23541122654f5bec41ef0a5657e5",
      "cs2_k": "f8546817671a440fd8df45b26fd6b45ebbf39e4207455ca12bc6d56ac0b35ebc"
    }
  ]
}
```

Reference test vectors are published in the JavaScript implementation at [ChainSafe/js-libp2p-noise PR #665](https://github.com/ChainSafe/js-libp2p-noise/pull/665) under `test/fixtures/pqc-test-vectors.json`, which holds five vectors, and are replayed by that implementation's test suite.

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
# PROTOCOL_ID = "/noise-mlkem768-hfs/0.2.0"

host = await new_node(
    security_opt={PROTOCOL_ID: TransportPQ(libp2p_keypair, noise_privkey)}
)
```

---

## 13. Interoperability Requirements

A conforming implementation MUST:

1. Use the exact protocol name string: `Noise_XXhfs_25519+MLKEM768_ChaChaPoly_SHA256`
2. Use raw ML-KEM-768 (FIPS 203) as the KEM primitive, not X-Wing or any other composite wrapper
3. Apply `encryptAndHash(cipherText)` BEFORE `mixKey(sharedSecret)` in the `ekem1` token
4. Transmit `e1.publicKey` as exactly 1,184 bytes in Message A (no AEAD tag at this stage)
5. Transmit `ekem1` as exactly 1,104 bytes in Message B (1,088-byte ciphertext + 16-byte AEAD tag)
6. Use the libp2p protocol identifier `/noise-mlkem768-hfs/0.2.0` for multistream negotiation
7. Pass the test vectors published by the reference implementation

---

## 14. Reference Implementations

Four implementations have been developed and tested against each other:

| Language | Repository | Status |
|----------|-----------|--------|
| TypeScript | [ChainSafe/js-libp2p-noise PR #665](https://github.com/ChainSafe/js-libp2p-noise/pull/665) | Draft PR; 99 tests, 5 deterministic test vectors |
| Python | [libp2p/py-libp2p PR #1310](https://github.com/libp2p/py-libp2p/pull/1310) | Draft PR; 56 tests |
| Rust | [libp2p/rust-libp2p PR #6481](https://github.com/libp2p/rust-libp2p/pull/6481), by @royzah; interop harness in [royzah/rust-libp2p PR #1](https://github.com/royzah/rust-libp2p/pull/1) | Draft PR; uses `ml-kem` crate (RustCrypto) |
| Nim | [vacp2p/nim-libp2p PR #2811](https://github.com/vacp2p/nim-libp2p/pull/2811) | Draft PR; ML-KEM-768 via BoringSSL |

### Interoperability Matrix (2026-09-17)

Every ordered (listener, dialer) pairing of the four implementations, including each implementation against itself, was run three times over loopback TCP on one Windows 11 machine: 48 runs, 48 passed. A run passes only if both sides exit cleanly, each side's reported peer identity matches the identity the other side printed for itself, and each side decrypts one encrypted transport message from the other, so both cipher states from the split are exercised in both roles.

| listener \ dialer | TypeScript | Python | Nim | Rust |
|---|---|---|---|---|
| **TypeScript** | 3/3 | 3/3 | 3/3 | 3/3 |
| **Python** | 3/3 | 3/3 | 3/3 | 3/3 |
| **Nim** | 3/3 | 3/3 | 3/3 | 3/3 |
| **Rust** | 3/3 | 3/3 | 3/3 | 3/3 |

The harnesses start the handshake directly on the TCP connection, without multistream-select, so identifier negotiation is not covered. The runner, results, per-run logs and two negative controls (an old-name build that fails against every other implementation, and a fabricated identity that the cross-check catches) are at [paschal533/pq-noise-artifacts](https://github.com/paschal533/pq-noise-artifacts/tree/main/interop).

An earlier revision of this section described a three-way test on 2026-06-24 as having exchanged encrypted transport messages. The harnesses used then verified the handshake only, and one pair's listener and dialer roles were reversed in the table. The matrix above replaces it.

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
