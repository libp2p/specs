# Libp2p error codes

## Connection Error Codes
| Name | Code | Description |
| --- | --- | --- |
| NO_ERROR | 0 | No reason provided for disconnection. This is equivalent to closing a connection or resetting a stream without any error code. | 
| Reserved For Transport | 0x1 - 0xfff | Reserved for transport level error codes. | 
| PROTOCOL_NEGOTIATION_FAILED | 0x1000 | Rejected because we couldn't negotiate a protocol. Used by multistream select for security negotiation | 
| RESOURCE_LIMIT_EXCEEDED | 0x1001 | Rejected because we ran into a resource limit. Implementations MAY retry with a backoff |
| RATE_LIMITED | 0x1002 | Rejected because the connection was rate limited. Implementations MAY retry with a backoff |
| PROTOCOL_VIOLATION | 0x1003 | Peer violated the protocol |
| SUPPLANTED | 0x1004 | Connection closed because a connection over a better tranpsort was available |
| GARBAGE_COLLECTED | 0x1005 | Connection was garbage collected |
| SHUTDOWN | 0x1006 | The node is shutting down |
| GATED | 0x1007 | The connection was gated. Most likely the IP / node is blacklisted. |
| CODE_OUT_OF_RANGE | 0x1008 | The error code received from the peer was greater than 4294967295(Max uint32).


## Stream Error Codes
| Name | Code | Description |
| --- | --- | --- |
| NO_ERROR | 0 | No reason provided for disconnection. This is equivalent to resetting a stream without any error code. | 
| Reserved For Transport | 0x1 - 0xfff | Reserved for transport level error codes. | 
| PROTOCOL_NEGOTIATION_FAILED | 0x1000 | Rejected because we couldn't negotiate a protocol. Used by multistream select|
| RESOURCE_LIMIT_EXCEEDED | 0x1001 | Stream rejected because we ran into a resource limit. Implementations MAY retry with a backoff |
| RATE_LIMITED | 0x1002 | Rejected because the connection was rate limited. Implementations MAY retry with a backoff |
| PROTOCOL_VIOLATION | 0x1003 | Rejected because the stream protocol was violated. MAY be used interchangably with `BAD_REQUEST` | 
| SUPPLANTED | 0x1004 | Resetted because a better transport is available for the stream |
| GARBAGE_COLLECTED | 0x1005 | Idle Stream was garbage collected |
| SHUTDOWN | 0x1006 | The node is shutting down |
| GATED | 0x1007 | The stream was gated. Most likely the IP / node is blacklisted. |
| CODE_OUT_OF_RANGE | 0x1008 | The error code received from the peer was greater than 4294967295(Max uint32).
