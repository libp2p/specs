8 Implementations
=================

A `libp2p` implementation should (recommended) follow a certain level of granulatiry when implementing different modules and functionalities, so that common interfaces are easy to expose, test and check for interoperability with other implementations.

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

  - JavaScript - <https://github.com/diasdavid/js-libp2p>
  - Go - <https://github.com/ipfs/go-ipfs>
  - Python - <https://github.com/candeira/py-ipfs/blob/readme-roadmap/README.md>
  - Rust - <https://github.com/diasdavid/rust-libp2p>

