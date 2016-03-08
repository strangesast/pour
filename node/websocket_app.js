var WebSocketServer = require('ws').Server;
var net = require('net');
var url = require('url');
var util = require('util'); // util.inspect
var Kegerator = require('./models/kegerator');

module.exports = function(server) {
  var wss = new WebSocketServer({
    server: server,
    path: '/sockets'
  });

  var activeKegerator = null;

  wss.on('connection', function connection(ws) {
    var loc = url.parse(ws.upgradeReq.url, true);

    ws.on('message', function(message) {
      var parsed;
      ws.send(JSON.stringify({
        type: 'message',
        message: 'received: ' + message
      }));

      try {
        parsed = JSON.parse(message);
      } catch (e) {
        return;
      }

      if(!parsed) {
        return;
      }

      if(parsed.currentHash && parsed.currentHash === "pouring") {
        if(activeKegerator !== null) {
          ws.send(JSON.stringify({
            type: "message",
            message: "begin pouring..."
          }));
        } else {
          ws.send(JSON.stringify({
            type: "message",
            message: "you must first set up kegerator"
          }));
        }
      } else if (parsed.activeKeg) {
        Kegerator.findById(parsed.activeKeg).then(function(result) {
          if(result) {
            activeKegerator = new net.Socket();
            activeKegerator.connect(result.port, result.address, function(err) {
              if(err) {
                return console.log(err);
              }
              ws.send(JSON.stringify({
                activeKeg: result.toJSON()
              }));
            });
            activeKegerator.on('error', function(err) {
              ws.send(JSON.stringify({
                type: 'message',
                message: 'failed to connect to "' + result.name + '"'
              }));
              activeKegerator = null;
            });
          } else {
            ws.send(JSON.stringify({
              type: "message",
              message: "kegerator not found"
            }));
          }

        }).catch(function(error) {
          ws.send(JSON.stringify({
            type: 'message',
            message: 'failed: ' + util.inspect(error)
          }));
        });
      } else if (parsed.action && parsed.action == "pour") {
        if(activeKegerator !== null) {

        }
      } else if (parsed.action && parsed.action == "temps") {

        if(activeKegerator !== null) {
          activeKegerator.on('data', function(data) {
            ws.send(JSON.stringify({
              type: "temperature_update",
              data: data.toString('utf-8')
            }));
          });
          activeKegerator.write('temps\n');
        }
      }

    });

    ws.send('welcome!');
  });
};
