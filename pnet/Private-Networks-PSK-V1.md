# Pre-shared Key Based Private Networks
This specification details the design and usage of Pre-shared Key Based Private Networks, or PSK Network, in IPFS.

## Encryption
* A PSK Network handles stream encryption via the XSalsa20 cipher.
* All network traffic, aside from the initial exchange of Nonce's, is encrypted.
* Authenticity of data is not performed by the PSK Network and should be handled by a separate encryption suite such as secio or TLS1.3.

### Enforcement
* A node exposed to the environment variable `LIBP2P_FORCE_PNET=1` when started, must enforce the existence of a PSK Network compliant protector.
  * If enforcement is turned on, and no protector is provided, the node must be terminated immediately.

### Private Shared Key
* A Private Shared Key is made available to the IPFS node, by adding a `swarm.key` file to the root of the IPFS Repo, prior to node creation.
* The key file must comply to the format detailed at [Private Shared Key Format](#private-shared-key-format)

#### Private Shared Key Format
* The Private Shared Key file, `swarm.key`, must contain 3 lines.
  * Line 1 must define the path-based multicodec for the key, `/key/swarm/psk/1.0.0/`.
  * Line 2 must define the path-based multicodec in which the Private Key, on Line 3, is encoded, such as `/base16/`.
  * Line 3 must contain the 32 byte Private Shared Key used for the private IPFS nodes, which must be encoded via the multicodec on Line 2.

##### PSK File Example
This example is for illustration purposes only. **DO NOT USE THIS KEY FOR PRODUCTION!!!**
```txt
/key/swarm/psk/1.0.0/
/base16/
0ff05394c733304ec26b3861ef23a4ffef9cd2e7d2040e028e5e9bb321d2eea3
```

## Cryptography of Private Networks (PNs)

The cryptography behind PNs was chosen to have a minimal resource overhead but to maintain security guarantees that connections should be established with and only with nodes sharing the same PSK. We have decided to encrypt all traffic, thus reducing the possible attack surface of protocols that are part of IPFS/libp2p.

It is important to mention that traffic in a private network is encrypted twice, once with PSK and once with the regular cryptographic stack for libp2p (secio or in the future TLS1.3). This allows the PSK layer to provide only above security guarantee, and for example not worrying about authenticity of the data. Possible replay attacks will be caught by the regular cryptographic layer above PNs layer.

### Choosing stream ciphers

We considered three stream ciphers: AES-CTR, Salsa20 and ChaCha. Salsa20 and ChaCha are very similar ciphers, as ChaCha is fully based on Salsa20. Unfortunately, due of ChaCha's lack of adoption, we were not able to find vetted implementations in relevant programming languages, which resulted in the ultimate consideration between AES-CTR and Salsa20.

There are three main reasons why we decided in favor of Salsa20 over AES-CTR:

1. We plan on using the same PSK among many nodes. This means that we need to randomize the nonce. For security the nonce collision should be a very unlikely event (frequently used value: 2<sup>-32</sup>). The Salsa20 family provides the XSalsa20 [[1][Xsalsa20]] stream cipher with a nonce of 192-bits. In comparison the usual mode of operation for AES-CTR usually operates with a 96-bit nonce. Which gives only `1.7e24` possible different nonces, and only `6.0e9` nonces form a birthday problem set with collision probability higher than 2<sup>-32</sup>. In case of XSalsa20 to reach the same collision probability, over `1e24` nonces have to be generated.
2.  The stream counter for the Salsa20 family is 64-bit long, and in composition with a 64 byte block size gives a total stream length of 2<sup>70</sup> bytes. This is more than will ever be transmitted through any connection (1ZiB). The AES-CTR (in its usual configuration of 96-bit nonce, 32-bit counter) with a block size of 16 bytes results in a stream length of 2<sup>36</sup>, which is only 64 GiB. It means that re-keying (re-nonceing in our case) would be necessary. As the nonce space is already much smaller for AES, re-nonceing would further increase nonce collision risk.
3. The speed was the last factor which was very important. The encryption layer is an added additional overhead. From our benchmarks, Salsa20 performs two times better on recent Intel 6th Generation processors and on ARM based processors (800MB/s vs 400MB/s and 13.5MB/s vs 7MB/s).

### Algorithm

The algorithm is very simple. A new nonce is created by each peer, is cross-shared with the other peer and XSalsa20 stream is initialized. After the 24 byte nonce, all traffic is encrypted using XSalsa20. If nodes are not using the same PSK, traffic from decryption will be unidentifiable, which will prevent any data exchange from higher layers.

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

[Xsalsa20]: https://cr.yp.to/snuffle/xsalsa-20081128.pdf
