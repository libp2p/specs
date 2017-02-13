# libp2p pubsub specification

This is the specification for generalized pubsub over libp2p. Pubsub in libp2p
is currently still experimental and this specification is subject to change.
This document does not go over specific implementation of pubsub routing
algorithms, it merely describes the common wire format that implementations
will use.

libp2p pubsub currently uses reliable ordered streams between peers. It assumes
that each peer is certain of the identity of each peer is it communicating
with.  It does not assume that messages between peers are encrypted, however
encryption defaults to being enabled on libp2p streams.

## The RPC

All communication between peers happens in the form of exchanging protobuf RPC
messages between participating peers.

The RPC protobuf is as follows:

```protobuf
message RPC {
	repeated SubOpts subscriptions = 1;
	repeated Message publish = 2;

	message SubOpts {
		optional bool subscribe = 1;
		optional string topicid = 2;
	}
}
```

This is a relatively simple message containing zero or more subscription
messages, and zero or more content messages. The subscription messages contain
a topicid string that specifies the topic, and a boolean signifying whether to
subscribe or unsubscribe to the given topic. True signifies 'subscribe' and
false signifies 'unsubscribe'. 

## The Message

The RPC message can contain zero or more messages of type 'Message' (perhaps
this should be named better?). The Message protobuf looks like this:

```protobuf
message Message {
	optional string from = 1;
	optional bytes data = 2;
	optional bytes seqno = 3;
	repeated string topicIDs = 4;
}
```

The `from` field denotes the author of the message, note that this is not
necessarily the peer who sent the RPC this message is contained in. This is
done to allow content to be routed through a swarm of pubsubbing peers. 

The `data` field is an opaque blob of data, it can contain any data that the
publisher wants it to. 

The `seqno` field is a linearly increasing, number unique among messages
originating from each given peer. No two messages on a pubsub topic from the
same peer should have the same seqno value, however messages from different
peers may have the same sequence number, so this number alone cannot be used to
address messages. (Notably the 'timecache' in use by the floodsub
implementation uses the concatenation of the seqno and the 'from' field) 

The `topicIDs` field specifies a set of topics that this message is being
published to. 

Note that messages are currently *not* signed. This will come in the near
future.

## The Topic Descriptor

The topic descriptor message is used to define various options and parameters
of a topic. It currently specifies the topics human readable name, its
authentication options, and its encryption options. 

The TopicDescriptor protobuf is as follows:

```protobuf
message TopicDescriptor {
	optional string name = 1;
	optional AuthOpts auth = 2;
	optional EncOpts enc = 3;

	message AuthOpts {
		optional AuthMode mode = 1;
		repeated bytes keys = 2;

		enum AuthMode {
			NONE = 0;
			KEY = 1;
			WOT = 2;
		}
	}

	message EncOpts {
		optional EncMode mode = 1;
		repeated bytes keyHashes = 2;

		enum EncMode {
			NONE = 0;
			SHAREDKEY = 1;
			WOT = 2;
		}
	}
}
```

The `name` field is a string used to identify or mark the topic, It can be
descriptive or random or anything the creator chooses. 

The `auth` field specifies how authentication will work for this topic. Only
authenticated peers may publish to a given topic. See 'AuthOpts' below for
details.

The `enc` field specifies how messages published to this topic will be
encrypted. See 'EncOpts' below for details.

### AuthOpts

The `AuthOpts` message describes an authentication scheme. The `mode` field
specifies which scheme to use, and the `keys` field is an array of keys. The
meaning of the `keys` field is defined by the selected `AuthMode`.

There are currently three options defined for the `AuthMode` enum:

#### AuthMode 'NONE'
No authentication, anyone may publish to this topic.

#### AuthMode 'KEY'
Only peers whose peerIDs are listed in the `keys` array may publish to this
topic, messages from any other peer should be dropped.

#### AuthMode 'WOT'
Web Of Trust, Any trusted peer may publish to the topic. A trusted peer is one
whose peerID is listed in the `keys` array, or any peer who is 'trusted' by
another trusted peer. The mechanism of signifying trust in another peer is yet
to be defined.


### EncOpts

The `EncOpts` message describes an encryption scheme for messages in a given
topic. The `mode` field denotes which encryption scheme will be used, and the
`keyHashes` field specifies a set of hashes of keys whose purpose may be
defined by the selected mode.

There are currently three options defined for the `EncMode` enum:

#### EncMode 'NONE'
Messages are not encrypted, anyone can read them.

#### EncMode 'SHAREDKEY'
Messages are encrypted with a preshared key. The salted hash of the key used is
denoted in the `keyHashes` field of the `EncOpts` message. The mechanism for
sharing the keys and salts is undefined.

#### EncMode 'WOT'
Web Of Trust publishing. Messages are encrypted with some certificate or
certificate chain shared amongst trusted peers. (Spec writers note: this is the
least clearly defined option and my description here may be wildly incorrect,
needs checking).
