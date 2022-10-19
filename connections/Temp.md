

#Testground multi-dimensional test matrix


### Tests are to be composed from the information extracted out of the resource files.

An example resource file entry may look like this:


    [[groups]]


    # go v0.42


    GoVersion = '1.18'


    Modfile = "go.v0.22.mod"


    Selector = 'v0.42'


    Implementation = 'go'


    SupportedTransports = ["tcp", "quic", "webrtc"]


    SupportedSecurityProtos = [“tls”, “noise”]


    SupportedMuxers = ["yamux", “mplex”]


###  A test peer/host  is customized by the following parameters: 

   testHost = Host(implementation, version, transport, securityProto, supportedMuxers)


### A test case is composed by two or more test hosts:

  testInstance = TestInstance(testHost-1, testHost2, …)


### Go transport list:

      Go-libp2p-transports = [“TCP”, “QUIC”, “Webtransport”, “Websocket”]


### Rust transport list:

      Rust-libp2p-transports = [“TCP”, “WebRTC”]


### JS transport list:

     JS-libp2p-transports[“ToDo”]    

Test Matrix

Test matrix for libp2p multi dimensional tests.  (Test cases should also be run with source/destination flipped)


<table>
  <tr>
   <td>Test case
   </td>
   <td colspan="5" ><strong>Source Host</strong>
   </td>
   <td rowspan="2" >Run
<p>
Test 
   </td>
   <td colspan="5" ><strong>Destination Host</strong>
   </td>
   <td colspan="2" >Expected Res
   </td>
  </tr>
  <tr>
   <td>
   </td>
   <td>Imp
   </td>
   <td>Ver
   </td>
   <td>Trans
   </td>
   <td>Sec
   </td>
   <td>Muxs
   </td>
   <td>Imp
   </td>
   <td>Ver
   </td>
   <td>Trans
   </td>
   <td>Sec
   </td>
   <td>Muxs
   </td>
   <td>Muxer
   </td>
   <td>RTT
   </td>
  </tr>
  <tr>
   <td>1
   </td>
   <td rowspan="5" >go
   </td>
   <td rowspan="5" >master
   </td>
   <td rowspan="5" >tcp
   </td>
   <td rowspan="5" >tls
   </td>
   <td rowspan="5" >ML1
   </td>
   <td rowspan="5" >X
   </td>
   <td>go
   </td>
   <td>1
   </td>
   <td>tcp
   </td>
   <td>tls
   </td>
   <td>ML1
   </td>
   <td>M1
   </td>
   <td>rtt-1
   </td>
  </tr>
  <tr>
   <td>2
   </td>
   <td>go
   </td>
   <td>cur
   </td>
   <td>tcp
   </td>
   <td>tls
   </td>
   <td>ML2
   </td>
   <td>M2
   </td>
   <td>rtt-1
   </td>
  </tr>
  <tr>
   <td>3
   </td>
   <td>go
   </td>
   <td>cur-1
   </td>
   <td>tcp
   </td>
   <td>tls
   </td>
   <td>ML1
   </td>
   <td>M1
   </td>
   <td>rtt
   </td>
  </tr>
  <tr>
   <td>4 
   </td>
   <td>go
   </td>
   <td>cur-2
   </td>
   <td>tcp
   </td>
   <td>tls
   </td>
   <td>ML1
   </td>
   <td>M1
   </td>
   <td>rtt
   </td>
  </tr>
  <tr>
   <td>5
   </td>
   <td>go
   </td>
   <td>cur-3
   </td>
   <td>tcp
   </td>
   <td>tls
   </td>
   <td>ML1
   </td>
   <td>M1
   </td>
   <td>rtt
   </td>
  </tr>
  <tr>
   <td>6
   </td>
   <td rowspan="5" >go
   </td>
   <td rowspan="5" >cur
   </td>
   <td rowspan="5" >tcp
   </td>
   <td rowspan="5" >noise
   </td>
   <td rowspan="5" >ML1
   </td>
   <td rowspan="5" >X
   </td>
   <td>go
   </td>
   <td>cur
   </td>
   <td>tcp
   </td>
   <td>noise
   </td>
   <td>ML1
   </td>
   <td>M1
   </td>
   <td>rtt-1
   </td>
  </tr>
  <tr>
   <td>7
   </td>
   <td>go
   </td>
   <td>cur
   </td>
   <td>tcp
   </td>
   <td>noise
   </td>
   <td>ML-2
   </td>
   <td>M1
   </td>
   <td>rtt-1
   </td>
  </tr>
  <tr>
   <td>8
   </td>
   <td>go
   </td>
   <td>cur-1
   </td>
   <td>tcp
   </td>
   <td>noise
   </td>
   <td>ML1
   </td>
   <td>M1
   </td>
   <td>rtt
   </td>
  </tr>
  <tr>
   <td>9 
   </td>
   <td>go
   </td>
   <td>cur-2
   </td>
   <td>tcp
   </td>
   <td>noise
   </td>
   <td>ML1
   </td>
   <td>M1
   </td>
   <td>rtt
   </td>
  </tr>
  <tr>
   <td>10
   </td>
   <td>go
   </td>
   <td>cur-3
   </td>
   <td>tcp
   </td>
   <td>noise
   </td>
   <td>ML1
   </td>
   <td>M1
   </td>
   <td>rtt
   </td>
  </tr>
  <tr>
   <td>11
   </td>
   <td rowspan="4" >go
   </td>
   <td rowspan="4" >cur
   </td>
   <td rowspan="4" >tcp
   </td>
   <td rowspan="4" >noise
   </td>
   <td rowspan="4" >ML1
   </td>
   <td rowspan="4" >X
   </td>
   <td>rust
   </td>
   <td>cur
   </td>
   <td>tcp
   </td>
   <td>noise
   </td>
   <td>ML1
   </td>
   <td>M1
   </td>
   <td>rtt
   </td>
  </tr>
  <tr>
   <td>12
   </td>
   <td>rust
   </td>
   <td>cur-1
   </td>
   <td>tcp
   </td>
   <td>noise
   </td>
   <td>ML1
   </td>
   <td>M1
   </td>
   <td>rtt
   </td>
  </tr>
  <tr>
   <td>13 
   </td>
   <td>rust
   </td>
   <td>cur-2
   </td>
   <td>tcp
   </td>
   <td>noise
   </td>
   <td>ML1
   </td>
   <td>M1
   </td>
   <td>rtt
   </td>
  </tr>
  <tr>
   <td>14
   </td>
   <td>rust
   </td>
   <td>cur-3
   </td>
   <td>tcp
   </td>
   <td>noise
   </td>
   <td>ML1
   </td>
   <td>M1
   </td>
   <td>rtt
   </td>
  </tr>
  <tr>
   <td>15
   </td>
   <td rowspan="5" >go
   </td>
   <td rowspan="5" >cur
   </td>
   <td rowspan="5" >tcp
   </td>
   <td rowspan="5" >tls
   </td>
   <td rowspan="5" >ML1
   </td>
   <td rowspan="5" >X
   </td>
   <td>JS
   </td>
   <td>cur
   </td>
   <td>tcp
   </td>
   <td>noise
   </td>
   <td>ML1
   </td>
   <td>M1
   </td>
   <td>rtt
   </td>
  </tr>
  <tr>
   <td>16
   </td>
   <td>JS
   </td>
   <td>cur
   </td>
   <td>tcp
   </td>
   <td>noise
   </td>
   <td>ML-2
   </td>
   <td>M1
   </td>
   <td>rtt
   </td>
  </tr>
  <tr>
   <td>17
   </td>
   <td>JS
   </td>
   <td>cur-1
   </td>
   <td>tcp
   </td>
   <td>noise
   </td>
   <td>ML1
   </td>
   <td>M1
   </td>
   <td>rtt
   </td>
  </tr>
  <tr>
   <td>18
   </td>
   <td>JS
   </td>
   <td>cur-2
   </td>
   <td>tcp
   </td>
   <td>noise
   </td>
   <td>ML1
   </td>
   <td>M1
   </td>
   <td>rtt
   </td>
  </tr>
  <tr>
   <td>19
   </td>
   <td>JS
   </td>
   <td>cur-3
   </td>
   <td>tcp
   </td>
   <td>noise
   </td>
   <td>ML1
   </td>
   <td>M1
   </td>
   <td>rtt
   </td>
  </tr>
  <tr>
   <td>
   </td>
   <td rowspan="4" >go
   </td>
   <td rowspan="4" >cur
   </td>
   <td rowspan="4" >QUIC
   </td>
   <td rowspan="4" >-
   </td>
   <td rowspan="4" >-
   </td>
   <td rowspan="4" >X
   </td>
   <td>go
   </td>
   <td>cur
   </td>
   <td>QUIC
   </td>
   <td>-
   </td>
   <td>-
   </td>
   <td>-
   </td>
   <td>
   </td>
  </tr>
  <tr>
   <td>
   </td>
   <td>go
   </td>
   <td>cur-1
   </td>
   <td>QUIC
   </td>
   <td>-
   </td>
   <td>-
   </td>
   <td>-
   </td>
   <td>
   </td>
  </tr>
  <tr>
   <td>
   </td>
   <td>go
   </td>
   <td>cur-2
   </td>
   <td>QUIC
   </td>
   <td>-
   </td>
   <td>-
   </td>
   <td>-
   </td>
   <td>
   </td>
  </tr>
  <tr>
   <td>
   </td>
   <td>go
   </td>
   <td>cur-3
   </td>
   <td>QUIC
   </td>
   <td>-
   </td>
   <td>-
   </td>
   <td>-
   </td>
   <td>
   </td>
  </tr>
  <tr>
   <td>
   </td>
   <td rowspan="4" >go
   </td>
   <td rowspan="4" >cur
   </td>
   <td rowspan="4" >WebTransport
   </td>
   <td rowspan="4" >-
   </td>
   <td rowspan="4" >-
   </td>
   <td rowspan="4" >X
   </td>
   <td>go
   </td>
   <td>cur
   </td>
   <td>WT
   </td>
   <td>-
   </td>
   <td>-
   </td>
   <td>-
   </td>
   <td>
   </td>
  </tr>
  <tr>
   <td>
   </td>
   <td>go
   </td>
   <td>cur-1
   </td>
   <td>WT
   </td>
   <td>-
   </td>
   <td>-
   </td>
   <td>-
   </td>
   <td>
   </td>
  </tr>
  <tr>
   <td>
   </td>
   <td>go
   </td>
   <td>cur-2
   </td>
   <td>WT
   </td>
   <td>-
   </td>
   <td>-
   </td>
   <td>-
   </td>
   <td>
   </td>
  </tr>
  <tr>
   <td>
   </td>
   <td>go
   </td>
   <td>cur-3
   </td>
   <td>WT
   </td>
   <td>-
   </td>
   <td>-
   </td>
   <td>-
   </td>
   <td>
   </td>
  </tr>
  <tr>
   <td>
   </td>
   <td rowspan="4" >go
   </td>
   <td rowspan="4" >cur
   </td>
   <td rowspan="4" >WS
   </td>
   <td rowspan="4" >-
   </td>
   <td rowspan="4" >-
   </td>
   <td rowspan="4" >X
   </td>
   <td>go
   </td>
   <td>cur
   </td>
   <td>WS
   </td>
   <td>-
   </td>
   <td>-
   </td>
   <td>-
   </td>
   <td>
   </td>
  </tr>
  <tr>
   <td>
   </td>
   <td>go
   </td>
   <td>cur-1
   </td>
   <td>WS
   </td>
   <td>-
   </td>
   <td>-
   </td>
   <td>-
   </td>
   <td>
   </td>
  </tr>
  <tr>
   <td>
   </td>
   <td>go
   </td>
   <td>cur-2
   </td>
   <td>WS
   </td>
   <td>-
   </td>
   <td>-
   </td>
   <td>-
   </td>
   <td>
   </td>
  </tr>
  <tr>
   <td>
   </td>
   <td>go
   </td>
   <td>cur-3
   </td>
   <td>WS
   </td>
   <td>-
   </td>
   <td>-
   </td>
   <td>-
   </td>
   <td>
   </td>
  </tr>
  <tr>
   <td>
   </td>
   <td rowspan="3" >rust
   </td>
   <td rowspan="3" >cur
   </td>
   <td rowspan="3" >TCP
   </td>
   <td rowspan="3" >noise
   </td>
   <td rowspan="3" >-
   </td>
   <td rowspan="3" >X
   </td>
   <td>JS
   </td>
   <td>cur
   </td>
   <td>TCP
   </td>
   <td>noise
   </td>
   <td>-
   </td>
   <td>
   </td>
   <td>
   </td>
  </tr>
  <tr>
   <td>
   </td>
   <td>JS
   </td>
   <td>
   </td>
   <td>
   </td>
   <td>
   </td>
   <td>
   </td>
   <td>
   </td>
   <td>
   </td>
  </tr>
  <tr>
   <td>
   </td>
   <td>
   </td>
   <td>
   </td>
   <td>
   </td>
   <td>
   </td>
   <td>
   </td>
   <td>
   </td>
   <td>
   </td>
  </tr>
  <tr>
   <td>
   </td>
   <td>
   </td>
   <td>
   </td>
   <td>
   </td>
   <td>
   </td>
   <td>
   </td>
   <td>
   </td>
   <td>
   </td>
   <td>
   </td>
   <td>
   </td>
   <td>
   </td>
   <td>
   </td>
   <td>
   </td>
   <td>
   </td>
  </tr>
</table>


ML1 = ["/yamux/1.0.0", "/mplex/6.7.0"]   M1 = “/yamux/1.0.0” , M2 = “/mplex/6.7.0”

ML2 = ["/mplex/6.7.0", "/yamux/1.0.0"]   ML3 = [“/mplex/6.7.0”]
