# Libp2p error codes

## TODO!
make this a CSV

## Connection Error Codes

| Name | Code | Description |
| --- | --- | --- |
| NO_ERROR | 0 | No reason provided for disconnection. This is equivalent to closing a connection or resetting a stream without any error code. | 
| Reserved For Transport | 0x1 - 0x1000 | Reserved for transport level error codes. | 
| GATED | 0x1001 | The connection was gated. Most likely the IP / node is blacklisted. |
| RESOURCE_LIMIT_EXCEEDED | 0x1002 | Rejected because we ran into a resource limit. Implementations MAY retry with a backoff |
| RATE_LIMITED | 0x1003 | Rejected because the connection was rate limited. Implementations MAY retry with a backoff |
| PROTOCOL_VIOLATION | 0x1004 | Peer violated the protocol |
| SUPPLANTED | 0x1005 | Connection closed because a connection over a better tranpsort was available |
| GARBAGE_COLLECTED | 0x1006 | Connection was garbage collected |
| SHUTDOWN | 0x1007 | The node is going down |
| PROTOCOL_NEGOTIATION_FAILED | 0x1008 | Rejected because we couldn't negotiate a protocol |


## Stream Error Codes

| Name | Code | Description |
| --- | --- | --- |
| NO_ERROR | 0 | No reason provided for disconnection. This is equivalent to resetting a stream without any error code. | 
| Reserved For Transport | 0x1 - 0x1000 | Reserved for transport level error codes. | 
| PROTOCOL_NEGOTIATION_FAILED | 0x1001 | Rejected because we couldn't negotiate a protocol |
| RESOURCE_LIMIT_EXCEEDED | 0x1002 | Connection rejected because we ran into a resource limit. Implementations MAY retry with a backoff |
| RATE_LIMITED | 0x1003 | Rejected because the connection was rate limited. Implementations MAY retry with a backoff |
| BAD_REQUEST | 0x1004 | Rejected because the request was invalid |
| PROTOCOL_VIOLATION | 0x1005 | Rejected because the stream protocol was violated. MAY be used interchangably with `BAD_REQUEST` | 
