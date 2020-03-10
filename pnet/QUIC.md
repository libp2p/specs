# Protecting QUIC Connections

This document describes how private networks (PN) are used with QUIC in libp2p.

The mechanism described here has the following design goals:
1. All unencrypted values on QUIC packets should be preserved. Among others, connection IDs are sent in the clear, and can be used by load balancers to inform routing decisions.
2. For a passive observer, it should be indistinguishable from a QUIC handshake that doesn't use the PN feature.
3. It should not add any significant overhead to the protocol. In specific, we want to avoid double encryption of a QUIC transfer.
4. It should not require any cooperation from the QUIC stack, therefore the mechanism can be used with any QUIC implemenation.


## Design

The encryption mechanism described in this document is intended to be implemented as a wrapper around a UDP socket, which parses - and under certain conditions described below encrypts - incoming and outgoing QUIC packets.

For a passive observer, a typical QUIC (as defined in the IETF draft versions and very likely in QUIC v1) handshake will look like this:

* The client sends a TLS 1.3 ClientHello in a packet with packet type [Initial](https://tools.ietf.org/html/draft-ietf-quic-transport-27#section-17.2.2). The server responds with a TLS 1.3 ServerHello in an Initial packet. Note that Initial packets are obfuscated with a key that depends on the connection ID used. An observer can therefore trivially decrypt this packet. From a security perspective, Initial packets are unprotected.
* The remainder of the TLS handshake uses packets with packet type [Handshake](https://tools.ietf.org/html/draft-ietf-quic-transport-27#section-17.2.4). These packets are encrypted with a key derived from values sent in ClientHello and ServerHello, so an outside observer is not able to decrypt them.
* Once the TLS handshake completes, endpoints switch to using packets with packet type [Short Header](https://tools.ietf.org/html/draft-ietf-quic-invariants-07#section-4.2). All application data is sent using those packets.

To implement PN for QUIC connections, we encrypt the **payload** of Handshake packets. The payload here means the bytes following the QUIC header.This fulfills the requirements listed above, because
1. The QUIC header is left untouched.
2. Initial packets (which are the only packets an observer can read) are left untouched.
3. The overhead is minimal, as there are only a few Handshake packets sent on every QUIC connection. 0-RTT and Short Header packets (which carry all the application data) are left untouched.
4. Encryption and decryption happen after an outgoing packet was sent out by the QUIC stack and before an incoming packet is passed to the QUIC stack.

Note that this mechanism assumes specifics of QUIC version 1. It MUST NOT be applied to other QUIC versions, unless this document (or a successor) specifies this.


## Specification

### Encryption Algorithm

The key used for encrypting Handshake packets is derived from the 32-byte PSK by running HKDF-Expand using SHA256 as the hash function and the “libp2p protector” as the context.
Packets are encrypted using ChaCha20 and an encryption scheme that is inspired by [QUIC’s header protection](https://tools.ietf.org/html/draft-ietf-quic-tls-27#section-5.4.4) algorithm:
The payload of the Handshake packets (i.e. all bytes remaining after the QUIC packet header) is split into two parts: the first 16 bytes and the rest. Since all QUIC ciphersuites use 16 byte AEAD tags (and QUIC forbids empty payloads), it is guaranteed that a valid QUIC packet has a payload that is at least 17 bytes long. The first 16 bytes are used as a sample.
The first 4 bytes of the sample are the block counter, the remaining 12 bytes are the counter. ChaCha20 is then invoked on the second part of the payload.
```
counter = sampe[0...3]
nonce = sample[4...15]
Ciphertext = ChaCha20(key, counter, nonce, rest of the payload)
```

The algorithm described here is symmetric for the receiving and the sending side.

### Processing QUIC packets

Since the protector is parsing the QUIC header, and parts of the QUIC header are version dependent, the protector needs to coordinate supported versions with the QUIC stack. Ideally, a protector will be able to process all QUIC versions that the QUIC stack supports.

When processing a QUIC packet, a PN implementation MUST parse the [QUIC Invariant Packet Header](https://tools.ietf.org/html/draft-ietf-quic-invariants-07#section-4). Short Header packets MUST be forwarded immediately.
For Long Header packets, the implementation MUST check the QUIC version number field. If the version number is 0, the packet is a [Version Negotiation Packet](https://tools.ietf.org/html/draft-ietf-quic-invariants-07#section-5), and MUST be forwarded immediately.
For all other Long Header packets, an implementation MUST check if it can decode the version-specific header of the QUIC packet. If that’s the case, and the packet is a QUIC Handshake packet, it applies the packet encryption algorithm described above.
If the protector processes a Long Header packet whose QUIC version it doesn’t support, it MUST NOT forward the packet, as this would allow for a QUIC handshake that is not PN protected. If this packet is an incoming packet, it SHOULD generate a QUIC Version Negotiation packet (listing the QUIC versions supported by the QUIC stack) before dropping the packet.
Implementations MUST process all parts of [coalesced packets](https://tools.ietf.org/html/draft-ietf-quic-transport-27#section-12.2), and apply the logic described above to any Handshake packet found in a coalesced packet.
