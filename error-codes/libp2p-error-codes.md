# Libp2p error codes

## Connection Error Codes
| Name | Code | Description |
| --- | --- | --- |
| NO_ERROR | 0 | No reason provided for disconnection. This is equivalent to closing a connection or resetting a stream without any error code. | 
| Reserved For Transport | 1 - 100 | Reserved for transport level error codes. | 
| PROTOCOL_NEGOTIATION_FAILED | 101 | Rejected because we couldn't negotiate a protocol. Used by multistream select for security negotiation | 
| RESOURCE_LIMIT_EXCEEDED | 102 | Rejected because we ran into a resource limit. Implementations MAY retry with a backoff |
| RATE_LIMITED | 103 | Rejected because the connection was rate limited. Implementations MAY retry with a backoff |
| PROTOCOL_VIOLATION | 104 | Peer violated the protocol |
| SUPPLANTED | 105 | Connection closed because a connection over a better tranpsort was available |
| GARBAGE_COLLECTED | 106 | Connection was garbage collected |
| SHUTDOWN | 107 | The node is shutting down |
| GATED | 108 | The connection was gated. Most likely the IP / node is blacklisted. |


## Stream Error Codes
| Name | Code | Description |
| --- | --- | --- |
| NO_ERROR | 0 | No reason provided for disconnection. This is equivalent to resetting a stream without any error code. | 
| Reserved For Transport | 1 - 100 | Reserved for transport level error codes. | 
| PROTOCOL_NEGOTIATION_FAILED | 101 | Rejected because we couldn't negotiate a protocol. Used by multistream select|
| RESOURCE_LIMIT_EXCEEDED | 102 | Stream rejected because we ran into a resource limit. Implementations MAY retry with a backoff |
| RATE_LIMITED | 103 | Rejected because the connection was rate limited. Implementations MAY retry with a backoff |
| PROTOCOL_VIOLATION | 104 | Rejected because the stream protocol was violated. MAY be used interchangably with `BAD_REQUEST` | 
| SUPPLANTED | 105 | Resetted because a better transport is available for the stream |
| GARBAGE_COLLECTED | 106 | Idle Stream was garbage collected |
| SHUTDOWN | 107 | The node is shutting down |
| GATED | 108 | The stream was gated. Most likely the IP / node is blacklisted. |
