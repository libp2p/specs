# libp2p AutoTLS

| Lifecycle Stage | Maturity       | Status | Latest Revision |
|-----------------|----------------|--------|-----------------|
| 1A              | Working Draft  | Active | r1, 2025-05-21  |

Authors: @gmelodie

Interest Group: TBD

[@gmelodie]: https://github.com/gmelodie

## Table of Contents

- [Introduction](#introduction)
- [General Flow](#general-flow)

## Overview
Most modern web browsers only establish TLS connections with peers that present certificates issued by a recognized Certificate Authority (CA). Self-signed certificates are generally not accepted. To obtain a CA-issued certificate, a requester must complete an ACME (Automatic Certificate Management Environment) challenge. This typically involves provisioning a DNS TXT record on a domain the requester controls.

However, most libp2p peers do not own or control domain names, making it impractical for them to complete DNS-based ACME challenges and, by extension, to obtain trusted TLS certificates. This limitation hinders direct communication between libp2p peers and standard web browsers.

AutoTLS addresses this problem by introducing an AutoTLS broker — a server that controls a domain and facilitates ACME challenges on behalf of libp2p peers. A peer can request the AutoTLS broker to fulfil an ACME DNS challenge on its behalf. Once the broker sets the appropriate DNS record, the requesting peer proceeds to notify the ACME server. The ACME server validates the challenge against the broker's domain, and if successful, issues a valid certificate.

This mechanism allows libp2p peers to obtain CA-issued certificates without needing to possess or manage their own domain names.

## General Flow
The following is the general flow of a successful certificate request and subsequent issuance using AutoTLS. Here, "client" refers to the machine running a libp2p peer and requesting the challenge, while "broker" and "AutoTLS broker", which are used interchangeably, is the server that will fulfil the ACME challenge on behalf of the client.

1. Client requests a challenge from the ACME server.
2. Client sends the challenge to the broker.
3. Broker tests client and sets DNS record (fulfilling challenge).
4. Client waits until the broker fulfils the challenge.
5. Client signals to ACME server that challenge is fulfilled.
6. ACME server checks challenge in broker.
7. Client finalizes certificate request (creates and sends CSR to ACME server).
8. Client waits until certificate is ready for download.
9. Client downloads certificate.

## Requesting challenge from ACME server
1. The client starts a libp2p peer with public IPv4 and support for `identify` protocol.
2. The client encodes its `PeerID` as [multibase base36](https://github.com/multiformats/multibase/blob/f378d3427fe125057facdbac936c4215cc777920/rfcs/Base36.md) of the CIDv1 of the multihash with the `libp2p-key` (`0x72`) multicodec:
    1. Transform PeerID into a multihash `mh`.
    2. Encode `mh` using [CIDv1](https://github.com/multiformats/cid?tab=readme-ov-file#cidv1) with the `libp2p-key` [multicodec](https://github.com/multiformats/multicodec)(`0x72`).
    3. Encode the CID data (if `cid` is the CID, then `cid.data.buffer` should be encoded) using [multibase base36](https://github.com/multiformats/multibase/blob/f378d3427fe125057facdbac936c4215cc777920/rfcs/Base36.md), which is the same as regular base36 without trimming leading zeroes and including a leading `k` or `K`) to get `b36peerid`.
3. The client generates a key `mykey` as specified in [RFC7518](https://www.rfc-editor.org/rfc/rfc7518#section-6).
4. The client registers an account on the ACME server (e.g. [production](https://acme-v02.api.letsencrypt.org) or [staging](https://acme-staging-v02.api.letsencrypt.org) servers for Let's Encrypt).
	1. Send a GET request to the `/directory` endpoint of the ACME server, and extract the `newAccount` value from the JSON response, which will be the registration URL we'll use.
	2. Send [JWT](https://www.rfc-editor.org/rfc/rfc7519)-signed POST request to registration URL with the following `payload`: `{"termsOfServiceAgreed": true}` (a `contact` field containing a list of `mailto:bob@example.org` contact information strings can also be optionally specified in the payload). The POST body is signed using JWT with `mykey` and `nonce` (`nonce` is a number returned by sending a GET request to the ACME server at the URL specified in `directory["newNonce"]`). The JSON payload using an RSA-256 key before JWT-signing should look like:
		```json
		{
		  "header": {
            "alg": "RS256",
            "typ": "JWT",
            "nonce": "`nonce`",
            "url": "`url`",
            "jwk": {
              "kty": "RSA",
              "n": "`mykey.n`",
              "e": "`mykey.e`"
            }
          },
		  "claims": {
            "payload": {
              "termsOfServiceAgreed": true,
              "contact": [
                "mailto:alice@example.com",
                "mailto:bob@example.com"
              ]
            }
          }
		}
		```
    The final body of any ACME request should look like:
		```json
		{
		  "payload": "`claims.toBase64`",
		  "protected": "`header.toBase64`",
		  "signature": "`base64UrlEncode(signature)`"
		}
		```
5. The client MUST save the `kid` present in the `location` header of the ACME server's response for in future requests to ACME server.
6. The client requests a certificate for the `*.{b36peerid}.libp2p.direct` domain from the ACME server by issuing a POST request using the same JWT signature scheme (and a new `nonce`) but using the `kid` field instead of the `jwk` field and containing the following JSON payload:
	```json
	{
		"type": "dns",
		"value": "*.{b36peerid}.libp2p.direct"
	}
	```
7. From the ACME server response, the client MUST save the entry with `"type"` of `"dns-01"` and derive the [`Key Authorization`](https://datatracker.ietf.org/doc/html/rfc8555#section-8.1) from that.

## Sending challenge to AutoTLS broker
1. The client sends the `key authorization` to the AutoTLS broker (e.g. `registration.libp2p.direct`). This requires a [PeerID Authentication](https://github.com/libp2p/specs/blob/master/http/peer-id-auth.md) between client and broker:
	1. Client sends GET request to the AutoTLS broker's `/v1/_acme-challenge` endpoint and extracts `challenge-client`, `public-key` and `opaque` from the `www-authenticate` response header.
	2. Client generates 32-character-long random string to be sent as a `challengeServer`. At the time of writing the PeerID Authentication specification does not contain recommendations about challenge length, but the official [`go-libp2p` implementation uses 32 characters](https://github.com/libp2p/go-libp2p/blob/master/p2p/http/auth/internal/handshake/handshake.go#L21).
	3. Client generates `sig`, `headers` and `payload` as follows, where `peer-privkey` is the private key of the client's libp2p peer and `multiaddrs` is a list of string representations of the libp2p peer's multiaddresses:
	```
		sig = base64URL(
			peer-privkey.sign(
				bytes(varint + "challenge-client={challenge-client}") +
				bytes(varint + "hostname={hostname}") +
				bytes(varint + "server-public-key={public-key}")
			)
		)

		headers = {
			"Content-Type": "application/json",
			"User-Agent": "some-user-agent",
			"authorization": "libp2p-PeerID public-key=\"{clientPublicKeyB64}\", opaque=\"{opaque}\", challenge-server=\"{challengeServer}\", sig=\"{sig}\""
		}

        payload = {
            "value": keyAuthorization,
            "addresses": multiaddrs
        }
	```
    **Note:** `varint` is a protobuf [varint](https://protobuf.dev/programming-guides/encoding/#varints) field that encodes the length of each of the `key=value` string.
    **Note:** the AutoTLS broker MUST NOT dial multiaddresses containing private IPv4 addresses, thus the client SHOULD only include multiaddresses that contain public IPv4 addresses in `multiaddrs`.
	4. Client sends a POST request to `/v1/_acme-challenge` endpoint using `payload` as body and `headers` as headers.
	6. Client SHOULD save the `bearer` token from the `authentication-info` response header, and use it for following requests to the AutoTLS broker.
3. Client SHOULD query DNS records (`TXT _acme-challenge.{b36peerid}.libp2p.direct` and `A dashed-public-ip-address.{b36peerid}.libp2p.direct`) until they are set by the AutoTLS broker.
4. Client notifies the ACME server about challenge completion so that the ACME server can lookup the DNS resource records. The notification is done in the form of a POST request with an empty JSON payload (`{}`) as body sent to the `url` field returned by the ACME server when it responded to client's initial challenge request.
	1. Client sends an empty signed JSON payload (`{}`) to the ACME server using the `kid` obtained from the initial ACME registration and gets the response from the server (`completedResponse`).
	2. Client extracts `url` field from `completedResponse`'s JSON body ting it, again with `kid` signing. The extracted URL is named `checkUrl` in this document.
5. The client polls the ACME server by sending an empty bodied, `kid` signed GET request to `checkUrl` until it receives a response with `status: valid` or `status: invalid` field, meaning that the challenge checking was successful or not, respectively.

## Signalling challenge completion to ACME server
11. Download certificate from ACME server.
## Finalizing challenge request
### CSR generation
## Downloading certificate from ACME server


## Complete certificate issuance example
