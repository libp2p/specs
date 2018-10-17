8 Implementations
=================

A `libp2p` implementation is recommended to follow a certain level of granularity when implementing different modules and functionalities, so that common interfaces are easy to expose, test and check for interoperability with other implementations.

This is the list of current modules available for `libp2p`:

  - libp2p (entry point)
  - **Swarm**
      - libp2p-swarm
      - libp2p-identify
      - libp2p-ping
      - Transports
          - [interface-transport](https://github.com/diasdavid/interface-transport)
          - [interface-connection](https://github.com/diasdavid/interface-connection)
          - libp2p-tcp
          - libp2p-udp
          - libp2p-udt
          - libp2p-utp
          - libp2p-webrtc
          - libp2p-cjdns
      - Stream Muxing
          - [interface-stream-muxer](https://github.com/diasdavid/interface-stream-muxer)
          - libp2p-spdy
          - libp2p-multiplex
      - Crypto Channel
          - libp2p-tls
          - libp2p-secio
  - **Peer Routing**
      - libp2p-kad-routing
      - libp2p-mDNS-routing
  - **Discovery**
      - libp2p-mdns-discovery
      - libp2p-random-walk
      - libp2p-railing
  - **Distributed Record Store**
      - libp2p-record
      - [interface-record-store](https://github.com/diasdavid/interface-record-store)
      - libp2p-distributed-record-store
      - libp2p-kad-record-store
  - **Generic**
      - PeerInfo
      - PeerId
      - multihash
      - multiaddr
      - multistream
      - multicodec
      - ipld
      - repo

Current known implementations (or WIP) are:

  - JavaScript - <https://github.com/libp2p/js-libp2p>
  - Go - <https://github.com/ipfs/go-libp2p>
  - Python - <https://github.com/candeira/py-ipfs/blob/readme-roadmap/README.md>
  - Rust - <https://github.com/libp2p/rust-libp2p>

## 8.1 Swarm

### 8.1.1 Swarm Dialer

The swarm dialer manages making a successful connection to a target peer, given a stream of addresses as inputs, and making sure to respect any and all rate limits imposed. To this end, we have designed the following logic for dialing:

```
DialPeer(peerID) {
	if PeerIsBeingDialed(peerID) {
		waitForDialToComplete(peerID)
		return BestConnToPeer(peerID)
	}
	
	StartDial(peerID)

	waitForDialToComplete(peerID)
	return BestConnToPeer(peerID)
}

	
StartDial(peerID) {
	addrs = getAddressStream(peerID)

	addrs.onNewAddr(function(addr) {
		if rateLimitCanDial(peerID, addr) {
			doDialAsync(peerID, addr)
		} else {
			rateLimitScheduleDial(peerID, addr)
		}
	})
}

// doDialAsync starts dialing to a specific address without blocking.
// when the dial returns, it releases rate limit tokens, and if it
// succeeded, will finalize the dial process.
doDialAsync(peerID, addr) {
	go transportDial(addr, function(conn, err) {
		rateLimitReleaseTokens(peerID, addr)

		if err != null {
			// handle error
		}

		dialSuccess(conn)
	})
}

// rateLimitReleaseTokens checks for any tokens the given dial
// took, and then for each of them, checks if any other dial is waiting
// for any of those tokens. If waiting dials are found, those dials are started
// immediately. Otherwise, the tokens are released to their pools.
rateLimitReleaseTokens(peerID, addr) {
	tokens = tokensForDial(peerID, addr)

	for token in tokens {
		dial = dialWaitingForToken(token)
		if dial != null {
			doDialAsync(dial.peer, dial.addr)
		} else {
			token.release()
		}
	}
	
}
```
