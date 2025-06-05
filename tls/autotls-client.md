# libp2p AutoTLS Client

| Lifecycle Stage | Maturity       | Status | Latest Revision |
|-----------------|----------------|--------|-----------------|
| 1A              | Working Draft  | Active | r1, 2025-05-21  |

Authors: @gmelodie

Interest Group: TBD

[@gmelodie]: https://github.com/gmelodie

## Table of Contents

- [Overview](#overview)
- [General Flow](#general-flow)
- [Requesting challenge from ACME server](#requesting-challenge-from-acme-server)
- [Sending challenge to AutoTLS broker](#sending-challenge-to-autotls-broker)
- [Signalling challenge completion to ACME server](#signalling-challenge-completion-to-acme-server)
- [Downloading certificate](#downloading-certificate)
- [Complete certificate issuance example](#complete-certificate-issuance-example)
- [References](#references)



## Overview
Most modern web browsers only establish TLS connections with peers that present certificates issued by a recognized Certificate Authority (CA).
Self-signed certificates are generally not accepted.
To obtain a CA-issued certificate, a requester must complete an ACME (Automatic Certificate Management Environment) challenge.
This typically involves provisioning a DNS TXT record on a domain the requester controls.

However, most libp2p peers do not own or control domain names, making it impractical for them to complete DNS-based ACME challenges and, by extension, obtain trusted TLS certificates.
This limitation hinders direct communication between libp2p peers and standard web browsers.

[AutoTLS](https://blog.libp2p.io/autotls/) addresses this problem by introducing an AutoTLS broker — a server that controls a domain and facilitates ACME challenges on behalf of libp2p peers.
A peer can request the AutoTLS broker to fulfill an ACME DNS challenge on its behalf.
Once the broker sets the appropriate DNS record, the requesting peer proceeds to notify the ACME server.
The ACME server validates the challenge against the broker's domain, and if successful, issues a valid certificate.

This mechanism allows libp2p peers to obtain CA-issued certificates without needing to possess or manage their own domain names.

## General Flow
The following is the general flow of a successful certificate request and subsequent issuance using AutoTLS.
Here, "node" refers to the machine running a libp2p peer and requesting the challenge,
while "broker" and "AutoTLS broker", which are used interchangeably, refer to the server that will fulfil the ACME challenge on behalf of the node.

1. Node requests a challenge from the ACME server.
2. Node sends the challenge to the broker.
3. Broker tests node and sets DNS record (fulfilling challenge).
4. Node queries DNS until it sees that the broker has fulfilled the challenge.
5. Node signals to ACME server that challenge is fulfilled.
6. ACME server checks challenge in broker.
7. Node sends CSR to finalize certificate request.
8. Node polls ACME server until certificate is ready for download.
9. Node downloads certificate.

## Parameters

| Parameter                | Description                                                      | Reasonable Default |
|--------------------------|------------------------------------------------------------------|--------------|
| `max_dns_retries` | The maximum number of DNS queries that the node SHOULD make before giving up | ???  |
| `max_dns_timeout` | The maximum number of seconds a node SHOULD wait for DNS records to be set | ???  |
| `max_acme_poll_retries` | The maximum number of GET requests that the node SHOULD issue to ACME server before giving up | ???  |
| `max_acme_timeout` | The maximum number of seconds a node SHOULD wait for an ACME resource status to change | ???  |

## Requesting challenge from ACME server
1. The node starts a libp2p peer with public IPv4 and support for the [`identify`](https://github.com/libp2p/specs/blob/master/identify/README.md) protocol.
2. The node encodes its `PeerID` as [multibase base36](https://github.com/multiformats/multibase/blob/f378d3427fe125057facdbac936c4215cc777920/rfcs/Base36.md) of the CIDv1 of the multihash with the `libp2p-key` (`0x72`) multicodec:
    1. Transform PeerID into a multihash `mh`.
    2. Encode `mh` using [CIDv1](https://github.com/multiformats/cid?tab=readme-ov-file#cidv1) with the `libp2p-key` [multicodec](https://github.com/multiformats/multicodec)(`0x72`).
    3. Encode the CID data using [multibase base36](https://github.com/multiformats/multibase/blob/f378d3427fe125057facdbac936c4215cc777920/rfcs/Base36.md), which is the same as regular base36 without trimming leading zeroes and including a leading `k` or `K`) to get `b36peerid`.

    **Note:** "CID data" are the raw bytes that compose the CID, not richer CID objects that contain more information.
3. The node generates a key `mykey` as specified in [RFC7518](https://www.rfc-editor.org/rfc/rfc7518#section-6).
4. The node registers an account on the ACME server (e.g. [production](https://acme-v02.api.letsencrypt.org) or [staging](https://acme-staging-v02.api.letsencrypt.org) servers for Let's Encrypt).
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
5. The node MUST save the `kid` present in the `location` header of the ACME server's response for future requests to the ACME server.
6. The node requests a certificate for the `*.{b36peerid}.libp2p.direct` domain from the ACME server by issuing a POST request using the same JWT signature scheme (and a new `nonce`) but using the `kid` field instead of the `jwk` field and containing the following JSON payload:
	```json
	{
      "identifiers": [
        {
          "type": "dns",
          "value": "*.{b36peerid}.libp2p.direct"
        }
      ]
	}
	```
7. From the ACME server response, the node MUST save the entry with `type` of `dns-01` and derive [`keyAuthorization`](https://datatracker.ietf.org/doc/html/rfc8555#section-8.1) from that.
8. From the ACME server response's `dns-01` field, the node MUST also save the value on the `url` field of the JSON body, here called `chalUrl`. This is used in the ACME signalling phase.
9. From the ACME server response's, the node MUST also save the value on the `location` header, here called `orderUrl`. This is used in the ACME signalling phase.
10. From the ACME server response's, the node MUST also save the value on the `finalize` field of the JSON body, here called `finalizeUrl`. This is used in the ACME signalling phase.




## Sending challenge to AutoTLS broker
1. The node sends `keyAuthorization` to the AutoTLS broker (e.g. `registration.libp2p.direct`). This requires a [peer ID authentication](https://github.com/libp2p/specs/blob/master/http/peer-id-auth.md) between node and broker:
	1. Node sends GET request to the AutoTLS broker's `/v1/_acme-challenge` endpoint and extracts `challenge-node`, `public-key` and `opaque` from the `www-authenticate` response header.
	2. Node generates 32-character-long random string to be sent as a `challengeServer`.

    **Note:** At the time of writing the PeerID Authentication specification does not contain recommendations about challenge length, but the official [`go-libp2p` implementation uses 32 characters](https://github.com/libp2p/go-libp2p/blob/master/p2p/http/auth/internal/handshake/handshake.go#L21).
	3. Node generates `sig`, `headers` and `payload` as follows, where `peer-privkey` is the private key of the node's libp2p peer and `multiaddrs` is a list of string representations of the libp2p peer's multiaddresses:
	```
		sig = base64URL(
			peer-privkey.sign(
				bytes(varint + "challenge-node={challenge-node}") +
				bytes(varint + "hostname={hostname}") +
				bytes(varint + "server-public-key={public-key}")
			)
		)

		headers = {
			"Content-Type": "application/json",
			"User-Agent": "some-user-agent",
			"authorization": "libp2p-PeerID public-key=\"{nodePublicKeyB64}\", opaque=\"{opaque}\", challenge-server=\"{challengeServer}\", sig=\"{sig}\""
		}

        payload = {
            "value": keyAuthorization,
            "addresses": multiaddrs
        }
	```

    **Note:** `varint` is a protobuf [varint](https://protobuf.dev/programming-guides/encoding/#varints) field that encodes the length of each of the `key=value` string.

    **Note:** The node SHOULD include only multiaddresses containing public IPv4 addresses in `multiaddrs`.
	4. Node sends a POST request to `/v1/_acme-challenge` endpoint using `payload` as HTTP body and `headers` as HTTP headers.
	5. Node SHOULD save the `bearer` token from the `authentication-info` response header, and use it for following requests to the AutoTLS broker.



## Signalling challenge completion to ACME server
1. Node SHOULD query DNS records (`TXT _acme-challenge.{b36peerid}.libp2p.direct` and `A dashed-public-ip-address.{b36peerid}.libp2p.direct`) until they are set by the AutoTLS broker.

**Note:** Here, `dashed-public-ip-address` is the public IPv4 address on in which the node received the confirmation dial from the broker.
For example, if the node has two public IPv4 addresses `1.1.1.1` and `8.8.8.8`, and the broker dialed it through `1.1.1.1`, then the node SHOULD query the `A 1-1-1-1.{b36peerid}.libp2p.direct`.

**Note:** The node SHOULD NOT send more than `max_dns_retries` DNS requests.
After `max_dns_timeout`, the communication is considered failed.
What to do after `max_dns_timeout` has passed is left as an implementation decision.

2. Node notifies the ACME server about challenge completion so that the ACME server can lookup the DNS resource records that the AutoTLS broker has set. The notification is done in the form of a POST request to `chalUrl` with an empty HTTP body (`{}`).
	1. Node sends an empty signed JSON payload (`{}`) to the ACME server using the `kid` obtained from the initial ACME registration and gets the response from the server (`completedResponse`).
	2. Node extracts `url` field from `completedResponse`'s JSON body. The extracted URL is named `checkUrl` in this document.
3. The node polls the ACME server by sending a GET HTTP request to `checkUrl` with an empty body, and sign using the `kid` of the registered account. The node MUST poll the ACME server until it receives a response with `status: valid` or `status: invalid` field, meaning that the challenge checking was successful or not, respectively.

**Note:** The node SHOULD NOT send more than `max_acme_poll_retries` poll requests to the ACME server.
After `max_acme_timeout`, the communication has failed.
What to do after `max_acme_timeout` has passed is left as an implementation decision.



## Downloading certificate
1. Node finalizes the certificate request:
    1. Generate CSR for the `*.{b36peerid}.libp2p.direct` domain.
    2. Encode the CSR with URL safe base 64 (`b64CSR`).
    3. Send a `kid` signed POST request to `finalizeUrl` with JSON HTTP body of `{"csr": b64CSR}`.
2. Node MUST poll ACME server by sending GET requests to `orderUrl` until the ACME server's response contains a `status` field with a value different than `processing`.

**Note:** The node SHOULD NOT send more than `max_acme_poll_retries` poll requests to the ACME server.
After `max_acme_timeout`, the communication has failed.
What to do after `max_acme_timeout` has passed is left as an implementation decision.

3. Node downloads finalized certificate by sending a GET request to `certDownloadUrl`.
`certDownloadUrl` is found in the `certificate` field of the JSON HTTP body of a response to a GET request to `orderUrl`.


## Complete certificate issuance example
In this example the node at `142.93.194.175` and with peer ID `12D3KooWATZi2wFwQxQ14Z3q24TDNWKap6f8W5ryLE6Da4RMfsxy`.

1. Node encodes its peer ID to multicode base 36: `k51qzi5uqu5dgf513xbrfjl4smgo2eh1x8p8y6grzsf1oz0reiy56p65tds3s6`

2. Node generates an RSA key and registers with ACME server by issuing a POST HTTP request to `https://acme-staging-v02.api.letsencrypt.org` with the following JSON body:
    ```json
    {
      "header": {
        "alg": "RS256",
        "typ": "JWT",
        "nonce": "1jOOXM0FEc7tL_RH3PbFWf5Ml4QXTrtG-d2faH_j68L9K27-768",
        "url": "https://acme-staging-v02.api.letsencrypt.org/acme/new-acct",
        "jwk": {
          "kty": "RSA",
          "n": "xImaldcbdCDn_IHSa2qeYjOhQ5PLuqIWLXEwQvvzD6eUIC8MteHvSM9Yj4tUGUzQ6Vic7j5j3npZhrmXMv3FiwIpQgsqDEiXSyriST7zYSPtQUcZr17gEqk9Rxjewl77HKkTej34IQ7JLaHzx5owJVtNsfBI36NPQiBCDaEBMht0E5zyMa83fTlNqnVnyMAqOR7CxctsxmYkoyyYeA_hV0gJfOBzUHls_ENHP67dQ2eVYGJ0gU7ldaK7lsWw10ieNCEDjbDT9E50HAdQt4UO1c_6rD8jzD0UjS2xtO6wrJpkmUnkt71WoQXWIWjoTvhl15dqLwyx_jeW-C6ISpwh1eWdrcM0z0TZpOZQEODg1IJppOEQZsBYeSZg4El5rt1IKcllp6euWlHPopreFNcEUrYZ76uQQLuRyQ2AM_caUITFi6e0ZgTea2COuy4vof2ZJTBZP8uE4aHUdXOMYrDO6TVnXYA7mYJ6jkyp-X9OjzGSst6yRY5Qm-uCmBEuVtoN",
          "e": "AQAB"
        }
      },
      "claims": {
        "termsOfServiceAgreed": true
      }
    }
    ```
    Which, after JWT signing, becomes:
    ```json
    {
      "payload": "eyJpZGVudGlmaWVycyI6W3sidHlwZSI6ImRucyIsInZhbHVlIjoiKi5rNTFxemk1dXF1NWRnZjUxM3hicmZqbDRzbWdvMmVoMXg4cDh5NmdyenNmMW96MHJlaXk1NnA2NXRkczNzNi5saWJwMnAuZGlyZWN0In1dfQ",
      "protected": "eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCIsIm5vbmNlIjoiWW8xc2xCY2RhV3FZREoyanFPYkhIb0dUZkZkQlJubzJzM2pzRGxQN2VNdXo5T1lDNWpBIiwidXJsIjoiaHR0cHM6Ly9hY21lLXN0YWdpbmctdjAyLmFwaS5sZXRzZW5jcnlwdC5vcmcvYWNtZS9uZXctb3JkZXIiLCJraWQiOiJodHRwczovL2FjbWUtc3RhZ2luZy12MDIuYXBpLmxldHNlbmNyeXB0Lm9yZy9hY21lL2FjY3QvMjAxNDI3MzQ0In0",
      "signature": "f2oPdLiFYwvv7_KLaiSlBgJJh3brXDA9_wPfw52UB_GTU0eL_9y9-oX8WJJcEU87juUWUuML3eEOT4zjUY1EK2ri-rR_8AO2QngpxpWbo86wUM-XwiXk35uGelpW0QvCQw_x16AWK6xr0Rm1gSbnVkxOMrMBl-2xQYyXILwLmEuTq76C2vt2ZzrLhcV-6BKUla2lkgaZKPK3dpTYL0_i0pEybb28Ree5SERHpxihxFTO1ggvLJosbdlGOtAvCc7x-aZhTcuwhjlCRNLi0rnsFRNh3PJc-_Kz5B2Uv_OoTktWg_0vrUU_OFBuf4lHl5lb82cl5NxRH9ieX673rsh9in9l9Nr-Gt3g8SdiY29LTMwOy37MmhhNcL7MjUcseI05FOhLFxyc3dUxsG92VSDwJ_1JQIQH7EGJ6vP_dDPustMlvzNX_qHV2TjN6XpAv2tECmK5enU7qfnhTXbPihvz7MY1_PAlxJSWmBq-ui_sovN85YNJWBZ-tIPOPtqPMZDT"
    }
    ```

3. Node requests a certificate for `*.k51qzi5uqu5dgf513xbrfjl4smgo2eh1x8p8y6grzsf1oz0reiy56p65tds3s6.libp2p.direct` by issuing a POST request to `https://acme-staging-v02.api.letsencrypt.org/acme/new-order` with the following JSON body:
    ```json
    {
      "header": {
        "alg": "RS256",
        "typ": "JWT",
        "nonce": "Yo1slBcdaWqYDJ2jqObHHoGTfFdBRno2s3jsDlP7eMuz9OYC5jA",
        "url": "https://acme-staging-v02.api.letsencrypt.org/acme/new-order",
        "kid": "https://acme-staging-v02.api.letsencrypt.org/acme/acct/201427344"
      },
      "claims": {
        "identifiers": [
          {
            "type": "dns",
            "value": "*.k51qzi5uqu5dgf513xbrfjl4smgo2eh1x8p8y6grzsf1oz0reiy56p65tds3s6.libp2p.direct"
          }
        ]
      }
    }
    ```

4. From the ACME server's response, node saves `orderUrl`, `chalUrl` and `finalizeUrl`:
    ```
    orderUrl: https://acme-staging-v02.api.letsencrypt.org/acme/order/201427344/24815752984
    chalUrl: https://acme-staging-v02.api.letsencrypt.org/acme/chall/201427344/17523856954/k8-vYA
    finalizeUrl: https://acme-staging-v02.api.letsencrypt.org/acme/finalize/201427344/24815752984
    ```

5. Node generates `keyAuthorization` (`jP5hwrZwCbP_qeeET_qAa9pgG0YulNaR0ivruESzCrE`) from the following `dns-01` object:
    ```json
    {
      "type": "dns-01",
      "url": "https://acme-staging-v02.api.letsencrypt.org/acme/chall/201427344/17523856954/k8-vYA",
      "status": "pending",
      "token": "nE2YGvFXzAy6UsFjYxqYOyA6rxZ7VJeQppsQ72hHyPM"
    }
    ```

6. Node authenticates with AutoTLS broker at `"https://registration.libp2p.direct/v1/_acme-challenge"` (refer to the [peer ID authentication spec](https://github.com/libp2p/specs/blob/master/http/peer-id-auth.md) for guidance and examples) and sends the following JSON body:
    ```json
    {
      "value": "jP5hwrZwCbP_qeeET_qAa9pgG0YulNaR0ivruESzCrE",
      "addresses": [
        "/ip4/142.93.194.175/tcp/49309"
      ]
    }
    ```

**Note:** the node's multiaddresses are `/ip4/127.0.0.1/tcp/49309`, `/ip4/142.93.194.175/tcp/49309`, `/ip4/10.17.0.5/tcp/49309`, and `/ip4/10.108.0.2/tcp/49309`, but only `/ip4/142.93.194.175/tcp/49309` contains a public IPv4 address, so node SHOULD only send that.

7. Node saves the bearer token (`bJNzn30OvOSIPsd0UtMygo4ccjUMXkwHONRHc46oyTx7ImlzLXRva2VuIjp0cnVlLCJwZWVyLWlkIjoiMTJEM0tvb1dBVFppMndGd1F4UTE0WjNxMjRURE5XS2FwNmY4VzVyeUxFNkRhNFJNZnN4eSIsImhvc3RuYW1lIjoicmVnaXN0cmF0aW9uLmxpYnAycC5kaXJlY3QiLCJjcmVhdGVkLXRpbWUiOiIyMDI1LTA1LTIyVDE0OjAxOjU4LjY1NzAyMDQ4OFoifQ==`) from the broker's `authentication-info` response header:
    ```
    Authentication-Info: libp2p-PeerID sig="hysWRh0SAQX6MkhNIwf0rgyjqbV9wkjMDhNobVhHybBE3CygrOAfEPTkvgrrePX5XTGt1FO-4--VBbJas8BtCQ==", bearer="bJNzn30OvOSIPsd0UtMygo4ccjUMXkwHONRHc46oyTx7ImlzLXRva2VuIjp0cnVlLCJwZWVyLWlkIjoiMTJEM0tvb1dBVFppMndGd1F4UTE0WjNxMjRURE5XS2FwNmY4VzVyeUxFNkRhNFJNZnN4eSIsImhvc3RuYW1lIjoicmVnaXN0cmF0aW9uLmxpYnAycC5kaXJlY3QiLCJjcmVhdGVkLXRpbWUiOiIyMDI1LTA1LTIyVDE0OjAxOjU4LjY1NzAyMDQ4OFoifQ=="
    ```
8. Node queries DNS records: `TXT _acme-challenge.k51qzi5uqu5dgf513xbrfjl4smgo2eh1x8p8y6grzsf1oz0reiy56p65tds3s6.libp2p.direct` and `A 142-93-194-175.k51qzi5uqu5dgf513xbrfjl4smgo2eh1x8p8y6grzsf1oz0reiy56p65tds3s6.libp2p.direct` until it receives a non-empty response from DNS servers.

9. Node notifies ACME server about challenge completion by issuing an empty POST request to `chalUrl` with `kid` JWT signing:
    ```json
    {
      "header": {
        "alg": "RS256",
        "typ": "JWT",
        "nonce": "Yo1slBcd5jWarMN9llbXOVII-htMZpSZBumnZAaKdyzqjyNfREg",
        "url": "https://acme-staging-v02.api.letsencrypt.org/acme/chall/201427344/17523856954/k8-vYA",
        "kid": "https://acme-staging-v02.api.letsencrypt.org/acme/acct/201427344"
      },
      "claims": {}
    }
    ```
    Node extracts `checkUrl` (`https://acme-staging-v02.api.letsencrypt.org/acme/chall/201427344/17523856954/k8-vYA`) from `url` field from ACME server's response body:
    ```json
    {
      "type": "dns-01",
      "url": "https://acme-staging-v02.api.letsencrypt.org/acme/chall/201427344/17523856954/k8-vYA",
      "status": "pending",
      "token": "nE2YGvFXzAy6UsFjYxqYOyA6rxZ7VJeQppsQ72hHyPM"
    }
    ```

10. Node polls the ACME server by sending GET HTTP requests to `checkUrl` until it receives a response with `status: valid`:
    ```json
    {
      "type": "dns-01",
      "url": "https://acme-staging-v02.api.letsencrypt.org/acme/chall/201427344/17523856954/k8-vYA",
      "status": "valid",
      "validated": "2025-05-22T14:01:59Z",
      "token": "nE2YGvFXzAy6UsFjYxqYOyA6rxZ7VJeQppsQ72hHyPM",
      "validationRecord": [
        {
          "hostname": "k51qzi5uqu5dgf513xbrfjl4smgo2eh1x8p8y6grzsf1oz0reiy56p65tds3s6.libp2p.direct"
        }
      ]
    }
    ```

11. Node creates the CSR:
    ```
    MIIBJzCBzgIBADAAMFkwEwYHKoZIzj0CAQYIKoZIzj0DAQcDQgAE-xJPmWkXNCxikFNfjX-YpNpVUlwVE75FqiLzQKqz0oSRGChnxEiCPXSYW6XYfy7RyYtoaMKJB8oYjpuoZau2U6BsMGoGCSqGSIb3DQEJDjFdMFswWQYDVR0RBFIwUIJOKi5rNTFxemk1dXF1NWRnZjUxM3hicmZqbDRzbWdvMmVoMXg4cDh5NmdyenNmMW96MHJlaXk1NnA2NXRkczNzNi5saWJwMnAuZGlyZWN0MAoGCCqGSM49BAMCA0gAMEUCIA_wWAa07lkYDlXVs8QBxX9XI7ATyMT8KIWirx2dBwyVAiEA9anNGq3BssBdMKW-QHKdOPqcv7lzaB64vTjpfciyfr4="
    ```
    And sends it to `finalizeUrl`:
    ```json
    {
      "header": {
        "alg": "RS256",
        "typ": "JWT",
        "nonce": "Yo1slBcdhW7xgUkJ0DzYeH1otfpMMbjbXD3xlf7TM1lneccMLHI",
        "url": "https://acme-staging-v02.api.letsencrypt.org/acme/finalize/201427344/24815752984",
        "kid": "https://acme-staging-v02.api.letsencrypt.org/acme/acct/201427344"
      },
      "claims": {
        "csr": "MIIBJzCBzgIBADAAMFkwEwYHKoZIzj0CAQYIKoZIzj0DAQcDQgAE-xJPmWkXNCxikFNfjX-YpNpVUlwVE75FqiLzQKqz0oSRGChnxEiCPXSYW6XYfy7RyYtoaMKJB8oYjpuoZau2U6BsMGoGCSqGSIb3DQEJDjFdMFswWQYDVR0RBFIwUIJOKi5rNTFxemk1dXF1NWRnZjUxM3hicmZqbDRzbWdvMmVoMXg4cDh5NmdyenNmMW96MHJlaXk1NnA2NXRkczNzNi5saWJwMnAuZGlyZWN0MAoGCCqGSM49BAMCA0gAMEUCIA_wWAa07lkYDlXVs8QBxX9XI7ATyMT8KIWirx2dBwyVAiEA9anNGq3BssBdMKW-QHKdOPqcv7lzaB64vTjpfciyfr4="
      }
    }
    ```
12. Node polls `orderUrl` until the ACME server's response contains a `status` field with value different than `processing`:
    ```json
    {
      "status": "valid",
      "expires": "2025-05-29T14:01:58Z",
      "identifiers": [
        {
          "type": "dns",
          "value": "*.k51qzi5uqu5dgf513xbrfjl4smgo2eh1x8p8y6grzsf1oz0reiy56p65tds3s6.libp2p.direct"
        }
      ],
      "authorizations": [
        "https://acme-staging-v02.api.letsencrypt.org/acme/authz/201427344/17523856954"
      ],
      "finalize": "https://acme-staging-v02.api.letsencrypt.org/acme/finalize/201427344/24815752984",
      "certificate": "https://acme-staging-v02.api.letsencrypt.org/acme/cert/2cd1c21b2b77127e4d394eb16eb073f9248d"
    }
    ```

13. Node downloads the certificate by sending a GET request to `certDownloadUrl` (`https://acme-staging-v02.api.letsencrypt.org/acme/cert/2cd1c21b2b77127e4d394eb16eb073f9248d`), which is the `certificate` field of the finalize request's response:
    ```
    -----BEGIN CERTIFICATE-----
    MIID3zCCA2SgAwIBAgISLNHCGyt3En5NOU6xbrBz+SSNMAoGCCqGSM49BAMDMFMx
    CzAJBgNVBAYTAlVTMSAwHgYDVQQKExcoU1RBR0lORykgTGV0J3MgRW5jcnlwdDEi
    MCAGA1UEAxMZKFNUQUdJTkcpIEZhbHNlIEZlbm5lbCBFNjAeFw0yNTA1MjIxMzAz
    MzJaFw0yNTA4MjAxMzAzMzFaMAAwWTATBgcqhkjOPQIBBggqhkjOPQMBBwNCAAT7
    Ek+ZaRc0LGKQU1+Nf5ik2lVSXBUTvkWqIvNAqrPShJEYKGfESII9dJhbpdh/LtHJ
    i2howokHyhiOm6hlq7ZTo4ICaTCCAmUwDgYDVR0PAQH/BAQDAgeAMB0GA1UdJQQW
    MBQGCCsGAQUFBwMBBggrBgEFBQcDAjAMBgNVHRMBAf8EAjAAMB0GA1UdDgQWBBT/
    wwgAeNwsd900zIITjOK2+Zjt7TAfBgNVHSMEGDAWgBShdBoGbVC3hi1KLMF+tI2I
    SWzNFjA2BggrBgEFBQcBAQQqMCgwJgYIKwYBBQUHMAKGGmh0dHA6Ly9zdGctZTYu
    aS5sZW5jci5vcmcvMFwGA1UdEQEB/wRSMFCCTiouazUxcXppNXVxdTVkZ2Y1MTN4
    YnJmamw0c21nbzJlaDF4OHA4eTZncnpzZjFvejByZWl5NTZwNjV0ZHMzczYubGli
    cDJwLmRpcmVjdDATBgNVHSAEDDAKMAgGBmeBDAECATAxBgNVHR8EKjAoMCagJKAi
    hiBodHRwOi8vc3RnLWU2LmMubGVuY3Iub3JnLzE0LmNybDCCAQYGCisGAQQB1nkC
    BAIEgfcEgfQA8gB3AN2ZNPyl5ySAyVZofYE0mQhJskn3tWnYx7yrP1zB825kAAAB
    lvhNETkAAAQDAEgwRgIhAOlwytcyMH7HcggxOYMhRdZ8LIoKt2T/VqS/bsMupnmK
    AiEA8ed29c8/BGQ2Qzoezp7zc1gm7g6F7VyrzRlj29bpYTQAdwCwzIPlpfl9a698
    CcwoSQSHKsfoixMsY1C3xv0m4WxsdwAAAZb4TREnAAAEAwBIMEYCIQDtuHcbHonG
    cEuwgT8r73zcRyLJQOWpRpLAqYtFy0idfwIhAM9zywGUgthnkAilzw1LQYQOmKEf
    fquKAmPYn0UU8duIMAoGCCqGSM49BAMDA2kAMGYCMQD+CVoiLqEpSreQua2uzmHr
    0DAoQycGtGfPcBsMdUGxSN7y+VyuYLnSG4PqgPa3nqsCMQDQY9jPJzUjLwwg11Z2
    +ZhDTPiLY3NoLGxa4dh5/LWKaRL6Sz77brYwebRXEnNQKAo=
    -----END CERTIFICATE-----
    ```

## References
- [Announcing AutoTLS: Bridging the Gap Between libp2p and the Web](https://blog.libp2p.io/autotls/)
