# Topic Table Extension

| Lifecycle Stage | Maturity      | Status | Latest Revision |
| --------------- | ------------- | ------ | --------------- |
| 1A              | Working Draft | Active | r0, 2025-11-11  |

Authors: [@ppopth], [@raulk]

Interest Group:

[@ppopth]: https://github.com/ppopth
[@raulk]: https://github.com/raulk

See the [lifecycle document][lifecycle-spec] for context about the maturity level
and spec status.

[lifecycle-spec]: https://github.com/libp2p/specs/blob/master/00-framework-01-spec-lifecycle.md

## Overview

The current gossipsub protocol transmits full topic names within both messages and control signals.

If the topic name is too large compared to the total size of the packet, the overhead on the bandwidth is significant. For example, the topic name in Ethereum can be as long as 50 bytes while the payload is only 200 bytes.

This extension introduces topic table agreement between a pair of peers in the GossipSub hello packets. When the topic table is agreed, peers on both ends use a topic index in the table to reference the topic rather than the topic name in each message sent.

The message types that have to be changed to include topic indices instead include `Message`, `ControlIHave`, `ControlGraft`, `ControlPrune`, and `RPC_SubOpts`.

## Protocol

Define a topic bundle to be a set of topics and a bundle hash to be the last 4 bytes of the sha256 digest of the concatenation of all its topic strings, ordered lexicographically.

When a stream is opened, a hello packet which includes an orderd list of bundle hahes is sent and a hello packet is receved from the other peer as well. The order reflects the peer's preference for topic table construction, with higher-priority bundles listed first to achieve more compact varint encoding for frequently used topics.

Then we use the `Intersect` function defined below to derive the mutually agreed topic bundles. This function is symmetric, so both parties will have the same list of topic bundles.

After the topic bundles are agreed, the topic table is constructed by expanding each agreed bundle to its constituent topic list, concatenating all expanded topics into a single sequence, and assigning 1-based indices to create the substitution dictionary.

After we have the topic table constructed, when we would like to send a message with a topic name inside, we replace that topic name with its index in the table. When we receive a message with a topic index, we also use the same table to convert it back to the topic name. If we receive a message with a topic name instead of a topic index, we leave it as it is.

## Bundle intersection

Given two lists of bundle hashes, it
* first extracts the long common prefix of the two
* then find the common hashes from the rest and sort lexicographically

For example, if the two lists are [x,y,d,c,e] and [x,y,f,c,d], the output will be [x,y,c,d].

```go
type TopicBundleHash [4]byte

func Intersect(first, second []TopicBundleHash) (result []TopicBundleHash, err error) {
	// Find common prefix where elements at each index are equal in both slices.
	for i := 0; i < min(len(first), len(second)) && bytes.Equal(first[i][:], second[i][:]); i++ {
		result = append(result, first[i])
	}

	// Store the length of the matching prefix. This is our marker.
	prefixLen := len(result)

	// Build a set of the remaining elements in the first slice after the prefix.
	// For each remaining element in the second slice, if it exists in the set,
	// add it to the result. (Duplicates possible if not validated up front.)
	seen := make(map[string]struct{})
	for _, v := range first[prefixLen:] {
		seen[string(v[:])] = struct{}{}
	}
	for _, v := range second[prefixLen:] {
		if _, ok := seen[string(v[:])]; ok {
			result = append(result, v)
		}
	}

	// Sort the unordered tail lexicographically.
	unordered := result[prefixLen:]
	sort.Slice(unordered, func(i, j int) bool {
		return bytes.Compare(unordered[i][:], unordered[j][:]) < 0
	})

	return result, nil
}
```

## Protobuf

The protobuf messages are identical to those specified in the [gossipsub v1.3.0
specification](https://github.com/libp2p/specs/blob/master/pubsub/gossipsub/gossipsub-v1.3.md)
with the following  control message modifications:

```protobuf
message ControlExtensions {
	optional ExtTopicTable topicTableExtension = 4820938;
}
message ExtTopicTable {
	repeated bytes topicBundleHashes = 1;
}

message RPC {
	message SubOpts {
		// optional string topicid = 2; // moved to topicRef
		oneof topicRef {
			string topicid = 2;
			uint32 topicIndex = 3;
		}
	}
}
message Message {
    // optional string topic = 4; // moved to topicRef
	oneof topicRef {
		string topic = 4;
		uint32 topicIndex = 7;
	}
}
message ControlIHave {
	// optional string topicID = 1; // moved to topicRef
	oneof topicRef {
		string topicID = 1;
		uint32 topicIndex = 3;
	}
}
message ControlGraft {
	// optional string topicID = 1; // moved to topicRef
	oneof topicRef {
		string topicID = 1;
		uint32 topicIndex = 2;
	}
}
message ControlPrune {
	// optional string topicID = 1; // moved to topicRef
	oneof topicRef {
		string topicID = 1;
		uint32 topicIndex = 4;
	}
}
```
