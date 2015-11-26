6 Interfaces
============

`libp2p` is a conglomerate of several protocols working together to offer a common solid interface with talking with any other network addressable process. This is made possible by shimming current exist protocols and implementations through a set of explicit interfaces, from Peer Routing, Discovery, Stream Muxing, Transports, Connections and so on.

## 6.1 libp2p

libp2p, the top module that interfaces all the other modules that make a libp2p instance, must offer an interface for dialing to a peer and plugging in all of the modules (e.g. which transports) we want to support.



## 6.2 Peer Routing

![](https://raw.githubusercontent.com/diasdavid/abstract-peer-routing/master/img/badge.png)

A Peer Routing service offers a way for libp2p Node to find the PeerInfo of another Node, so that it can dial to that node. In it is most pure form, a Peer Routing module should have a interface that given a 'key', a set of PeerInfos are returned.
See https://github.com/diasdavid/abstract-peer-routing for the interface and tests.

## 6.3 Swarm

Current interface available and updated at:

https://github.com/diasdavid/js-libp2p-swarm#usage

### 6.3.1 Transport

![](https://raw.githubusercontent.com/diasdavid/abstract-transport/master/img/badge.png)

https://github.com/diasdavid/abstract-transport

### 6.3.2 Connection

![](https://raw.githubusercontent.com/diasdavid/abstract-connection/master/img/badge.png)

https://github.com/diasdavid/abstract-connection

### 6.3.3 Stream Muxing

![](https://github.com/diasdavid/abstract-stream-muxer/raw/master/img/badge.png)

https://github.com/diasdavid/abstract-stream-muxer

## 6.4 Distributed Record Store

![](https://raw.githubusercontent.com/diasdavid/abstract-record-store/master/img/badge.png)

https://github.com/diasdavid/abstract-record-store


## 6.5 Peer Discovery


