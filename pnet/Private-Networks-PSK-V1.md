## Pre-shared Key Based Private Networks in libp2p

This document describes the first version of private networks (PN) featured in libp2p.

For the first implementation, only pre-shared key (PSK) functionality is available, as the Public Key Infrastructure approach is much more complex and requires more technical preparation.

It was implemented as an additional encryption layer before any libp2p traffic, and was designed to leak the absolute minimum of information on its own. All traffic leaving the node inside a PN is encrypted and there is no characteristic handshake.

### Interface

An libp2p node or libp2p swarm is either in a a public network, or it is a member of a private network.

A private network is defined by the 256-bit secret key, which has to be known and used by all members inside the network.

In the case of an libp2p node, this key is stored inside the libp2p repo in a file named `swarm.key`. The file uses a path-based multicodec where, for now, the codec that is defined and used is `/key/swarm/psk/1.0.0/`. The codec expects the next path-based multicodec to define the base encoding for the rest of the file (`/bin/`, `/base16/`, `/base64/`), which is the 256-bit PSK. The key has to be exactly 256-bits (32 bytes) long.

#### Security Guarantees

Nodes of different private networks must not be able to connect to each other. This extends to node in private network connecting to node in public network. This means that no information exchange, apart from the handshakeing required for private network authentication, should take place.

These guarnetee is only provided when knowledge of private key is limited to trusted party. 

#### Safeguard

In the libp2p swarm there is a safeguard implemented that prevents it from dialing with no PSK set, which would mean the node would connect with the rest of the public network.

It can be enabled by setting `LIBP2P_FORCE_PNET=1` in the environment before starting libp2p or any other libp2p based application. In the event that the node is trying to connect with no PSK, thus connecting to the public network, an error will be raised and the process will be aborted.

### Cryptography of Private Networks

The cryptography behind PNs was chosen to have a minimal resource overhead but to maintain security guarantees that connections should be established with and only with nodes sharing the same PSK. We have decided to encrypt all traffic, thus reducing the possible attack surface of protocols that are part of IPFS/libp2p.

It is important to mention that traffic in a private network is encrypted twice, once with PSK and once with the regular cryptographic stack for libp2p (secio or in the future TLS1.3). This allows the PSK layer to provide only above security guarantee, and for example not worrying about authenticity of the data. Possible replay attacks will be caught by the regular cryptographic layer above PNs layer.

#### Choosing stream ciphers

We considered three stream siphers: AES-CTR, Salsa20 and ChaCha. Salsa20 and ChaCha are very similar ciphers, as ChaCha is fully based on Salsa20. And unfortunately, due of ChaCha's lack of adoption, we were not able to find vetted implementations in relevant programming languages. Because of this, the final consideration was between AES-CTR and Salsa20.

There are three main reasons why we decided for Salsa20 over AES-CTR:

1. We plan on using the same PSK among many nodes. This means that we need to randomize the nonce. For security the nonce collision should be a very unlikely event (frequently used value: 2<sup>-32</sup>). The Salsa20 family provides the XSalsa20 [[1][Xsalsa20]] stream cipher with a nonce of 192-bits. In comparison the usual mode of operation for AES-CTR usually operates with a 96-bit nonce. Which gives only possible different `1.7e24` nonces , and only `6.0e9` nonces form a birthday problem set with collision probablity higher than 2<sup>-32</sup>. In case of XSalsa20 to reach the same collision probability over `1e24` nnonces have to be generated.
2.  The stream counter for the Salsa20 family is 64-bit long, and in composition with a 64 byte block size gives a total stream length of 2<sup>70</sup> bytes. This is more than will ever be transmitted through any connection (1ZiB). The AES-CTR (in its usual configuration of 96-bit nonce, 32-bit counter) with a block size of 16 bytes results in a stream length of 2<sup>36</sup>, which is only 64 GiB. It means that re-keying (re-nonceing in our case) would be necessary. As the nonce space is already much smaller for AES, re-nonceing would further increase nonce collision risk.
3. The speed was the last factor which was very important. The encryption layer is an added additional overhead. From our benchmarks, Salsa20 performs two times better on recent Intel 6th Generation processors and on ARM based processors (800MB/s vs 400MB/s and 13.5MB/s vs 7MB/s).

#### Algorithm

The algorithm is very simple. New nonce is created, it is corss-shared with the other party and XSalsa20 stream is initalized. After 24 bytes of random data (nonce), all traffic is encrypted using XSalsa20. If nodes are not using same PSK the traffic from decryption will be still scrambled which will prevent any data exchange from higher layers.

On Writing side:
```c
// (⊕ denotes bytewise xor operation)
SS = <shared secret>
N = randomNonce(24) // 24 byte nonce
write(out, N)       // send nonce
S20 = newXSalsa20Stream(SS, N)
for data = <data to send> {
  write(out, (data ⊕ S20))
}
```

On reading side
```c
// (⊕ denotes bytewise xor operation)
SS = <shared secret>
N = byte[24]        // 24 byte nonce
read(in, N)         // read nonce
S20 = newXSalsa20Stream(SS, N)
for data = read(in) {
  process(data ⊕ S20)
}
```

Where for each connection pair or reading and writing modules is created.

[Xsalsa20]: https://cr.yp.to/snuffle/xsalsa-20081128.pdf
