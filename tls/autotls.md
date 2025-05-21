# libp2p AutoTLS  <!-- omit in toc -->

| Lifecycle Stage | Maturity       | Status | Latest Revision |
|-----------------|----------------|--------|-----------------|
| ??              | ?????????????? | Active | r0, 2025-04-30  |

Authors: [@gmelodie]

Interest Group: [@??], [@???]

[@gmelodie]: https://github.com/gmelodie
[@??]: https://github.com/Stebalien
[@???]: https://github.com/jacobheun


See the [lifecycle document][lifecycle-spec] for context about the maturity level
and spec status.

[lifecycle-spec]: https://github.com/libp2p/specs/blob/master/00-framework-01-spec-lifecycle.md

## Table of Contents  <!-- omit in toc -->

- [Introduction](#introduction)
- [General Flow](#general-flow)

## Overview
Most modern web browsers only establish TLS connections with peers that present certificates issued by a recognized Certificate Authority (CA). Self-signed certificates are generally not accepted. To obtain a CA-issued certificate, a requester must complete an ACME (Automatic Certificate Management Environment) challenge. This typically involves provisioning a DNS TXT record on a domain the requester controls.

However, most libp2p peers do not own or control domain names, making it impractical for them to complete DNS-based ACME challenges and, by extension, to obtain trusted TLS certificates. This limitation hinders direct communication between libp2p peers and standard web browsers.

AutoTLS addresses this problem by introducing an AutoTLS broker — a server that controls a domain and facilitates ACME challenges on behalf of libp2p peers. A peer can request the AutoTLS broker to fulfill an ACME DNS challenge on its behalf. Once the broker sets the appropriate DNS record, the requesting peer proceeds to notify the ACME server. The ACME server validates the challenge against the broker's domain, and if successful, issues a valid certificate.

This mechanism allows libp2p peers to obtain CA-issued certificates without needing to possess or manage their own domain names.

## General Flow
1. Start libp2p client with public IPv4 (or IPv6) and support for `identify` protocol (standard for `nim-libp2p`)
2. Get `PeerID` as a base36 of the CID of the multihash with the `libp2p-key` (`0x72`) multicodec: 
	1. Transform PeerID into a multihash `mh`
	2. Transform `mh` into a `v1` CID with the `0x72` multicodec (`libp2p-key`)
	3. Base36 encode the `cid.data.buffer` (not regular base36! this one needs [multibase base36](https://github.com/multiformats/multibase/blob/f378d3427fe125057facdbac936c4215cc777920/rfcs/Base36.md), which is the same as regular base36 but doesn't trims leading zeroes and starts with a `k` or `K`) to get `b36peerid`
3. Generate an RSA key `mykey`
4. Register an account on the ACME server ([production server for Let's Encrypt](https://acme-v02.api.letsencrypt.org) or just the [staging server](https://acme-staging-v02.api.letsencrypt.org) for testing)
	1. Send a GET request to the `directory` endpoint, and extract the `newAccount` value from the JSON response, which will be the registration URL we'll use
	2. Signed POST request to registration URL with the following `payload`: `{"termsOfServiceAgreed": true}`. The actual POST body is signed using JWT with an `mykey` and `nonce` (gotten from `directory["newNonce"]`), so the final body of any ACME request should look like:
		```json
		{
		  "payload": token.claims.toBase64,
		  "protected": token.header.toBase64,
		  "signature": base64UrlEncode(token.signature),
		}
		```
		Obs: the response to the account registration contains a `kid` in the `location` field that should be saved and used in following requests to ACME server
5. Request a certificate for the `*.{b36peerid}.libp2p.direct` domain from the ACME server by issuing a POST request using the same JWT signature scheme (and another new `nonce` from `directory["newNonce"]`) but with `kid` instead of `jwk` field and the following payload:
	```json
	{
		"type": "dns",
		"value": "*.{b36peerid}.libp2p.direct"
	}
	```
6. From the ACME server response, get the entry with `"type"` of `"dns-01"` and derive the `Key Authorization` for it: 
	-  `sha256.digest((dns01Challenge["token"] + "." + thumbprint(key))` 
		-  [JWK thumbprint](https://www.rfc-editor.org/rfc/rfc7638): `base64encode(sha256.digest({"e": key.e, "kty": "RSA", "n": key.n}))`, but you can use other key types too
7. Send challenge to AutoTLS broker/server https://registration.libp2p.direct/, which requires a [PeerID Auth](https://github.com/libp2p/specs/blob/master/http/peer-id-auth.md) scheme:
	1. Send GET request to the `v1/_acme-challenge` endpoint and get `www-authenticate` field from the response header, and extract the values of three strings that it contains: `challenge-client`, `public-key` and `opaque`
	2. Generate random string with around 42 characters as a `challengeServer` of our own
	3. Get `peer-pubkey` and `peer-privkey` keys of our libp2p `peer`, which are not necessarily the same keys we're using to talk to ACME server
	4. `sig = ` (obs: `varint` is a protobuf [varint](https://protobuf.dev/programming-guides/encoding/#varints) field that encodes the length of the `key=value` string)
	```
		sig = base64URL(
			peer-privkey.sign(
				bytes(varint + "challenge-client={challenge-client}") +
				bytes(varint + "hostname={hostname}") +
				bytes(varint + "server-public-key={publicKey}")
			)
		)
	```
	5. `headers	 =`
		```json
		{
			"Content-Type": "application/json",
			"User-Agent": "nim-libp2p",
			"authorization": "libp2p-PeerID public-key=\"{clientPublicKeyB64}\", opaque=\"{opaque}\", challenge-server=\"{challengeServer}\", sig=\"{sig}\""
		}
		```
	6. Send POST to `v1/_acme-challenge` endpoint using `payload` as body and `headers`
	7. Get the `bearer` token from the `authentication-info` header of the response, which should be used for following requests from this client.
8. Check that the AutoTLS server has added the `_acme-challenge.{b36peerid}.libp2p.direct` `TXT` and the `dashed-public-ip-address.{b36peerid}.libp2p.direct` `A` DNS resource records.
9. Notify ACME server of challenge completion so it can lookup the DNS resource records.
	1. Get URL from `dns01challenge["url"]`
	2. Send an empty signed JSON payload (`{}`) to the ACME server using the `kid` obtained from the ACME registration step and get the response from the server (`completedResponse`).
	3. From `completedResponse`,  the `url` field from the JSON body by `GET`ting it, again with `kid` signing.
10. Wait for ACME server to finish testing the domain.
	- The response from the polling will contain a `status` field that will be `pending` while ACME is still testing the challenge, and `valid` or `invalid` when it's done.
11. Download certificate from ACME server.
