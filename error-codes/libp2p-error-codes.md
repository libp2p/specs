# Libp2p error codes

## Connection Error Codes
| Name | Code | Description |
| --- | --- | --- |
| NO_ERROR | 0 | No reason provided for disconnection. This is equivalent to closing a connection or resetting a stream without any error code. | 
| Reserved For Transport | 0x1 - 0x3ff | Reserved for transport level error codes. | 
| PROTOCOL_NEGOTIATION_FAILED | 0x400 | Rejected because we couldn't negotiate a protocol. Used by multistream select for security negotiation | 
| RESOURCE_LIMIT_EXCEEDED | 0x401 | Rejected because we ran into a resource limit. Implementations MAY retry with a backoff |
| RATE_LIMITED | 0x402 | Rejected because the connection was rate limited. Implementations MAY retry with a backoff |
| PROTOCOL_VIOLATION | 0x403 | Peer violated the protocol |
| SUPPLANTED | 0x404 | Connection closed because a connection over a better tranpsort was available |
| GARBAGE_COLLECTED | 0x405 | Connection was garbage collected |
| SHUTDOWN | 0x406 | The node is shutting down |
| GATED | 0x407 | The connection was gated. Most likely the IP / node is blacklisted. |
| CODE_OUT_OF_RANGE | 0x408 | The error code received from the peer was greater than 4294967295(Max uint32).


## Stream Error Codes
| Name | Code | Description |
| --- | --- | --- |
| NO_ERROR | 0 | No reason provided for disconnection. This is equivalent to resetting a stream without any error code. | 
| Reserved For Transport | 0x1 - 0x3ff | Reserved for transport level error codes. | 
| PROTOCOL_NEGOTIATION_FAILED | 0x400 | Rejected because we couldn't negotiate a protocol. Used by multistream select|
| RESOURCE_LIMIT_EXCEEDED | 0x401 | Stream rejected because we ran into a resource limit. Implementations MAY retry with a backoff |
| RATE_LIMITED | 0x402 | Rejected because the connection was rate limited. Implementations MAY retry with a backoff |
| PROTOCOL_VIOLATION | 0x403 | Rejected because the stream protocol was violated. MAY be used interchangably with `BAD_REQUEST` | 
| SUPPLANTED | 0x404 | Resetted because a better transport is available for the stream |
| GARBAGE_COLLECTED | 0x405 | Idle Stream was garbage collected |
| SHUTDOWN | 0x406 | The node is shutting down |
| GATED | 0x407 | The stream was gated. Most likely the IP / node is blacklisted. |
| CODE_OUT_OF_RANGE | 0x408 | The error code received from the peer was greater than 4294967295(Max uint32).
